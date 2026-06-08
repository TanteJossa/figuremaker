import math
import json
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import logging
from leerlevels_style import Canvas, draw_line, draw_arrow, draw_text, draw_rect, draw_circle, COLORS, SVGString

logger = logging.getLogger(__name__)

class SVGGroup(SVGString):
    """
    Groups elements into a single SVG <g id="..."> tag for vector editing,
    while permitting flat serialization into the structured JSON file.
    """
    def __new__(cls, group_id, sub_elements):
        svg_lines = [f'<g id="{group_id}">']
        for el in sub_elements:
            # Shift nested rendering slightly
            svg_lines.append(f'  {str(el)}')
        svg_lines.append('</g>')
        content = "\n".join(svg_lines)
        
        obj = str.__new__(cls, content)
        obj.group_id = group_id
        obj.sub_elements = sub_elements
        obj.metadata = None
        return obj

class SVGImage(SVGString):
    """
    Represents an image element in SVG and native Slides.
    """
    def __new__(cls, local_path, x, y, width, height, element_id):
        content = f'<image id="{element_id}" href="{local_path}" x="{x:.3f}" y="{y:.3f}" width="{width:.3f}" height="{height:.3f}" />'
        obj = str.__new__(cls, content)
        obj.metadata = {
            "type": "image",
            "id": element_id,
            "local_path": local_path,
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }
        return obj

class Viewport:
    """
    Coordinates transformation from abstract mathematical coordinates (X, Y)
    to physical canvas Presentation Points (PT) coordinates.
    """
    def __init__(self, x_min: float, x_max: float, y_min: float, y_max: float,
                 canvas_width: float = 1000, canvas_height: float = 562.5,
                 margin_left: float = 80, margin_right: float = 40,
                 margin_top: float = 40, margin_bottom: float = 60):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom
        
        # Calculate active plotting dimensions
        self.plot_width = canvas_width - margin_left - margin_right
        self.plot_height = canvas_height - margin_top - margin_bottom
        
        self.x_range = x_max - x_min
        self.y_range = y_max - y_min

    def map_x(self, math_x: float) -> float:
        if self.x_range == 0:
            return self.margin_left
        scale = self.plot_width / self.x_range
        return self.margin_left + (math_x - self.x_min) * scale

    def map_y(self, math_y: float) -> float:
        if self.y_range == 0:
            return self.margin_top + self.plot_height
        scale = self.plot_height / self.y_range
        # Y is inverted in screen space: top is margin_top, bottom is margin_top + plot_height
        return self.margin_top + self.plot_height - (math_y - self.y_min) * scale

    def map_coords(self, math_x: float, math_y: float) -> tuple[float, float]:
        return self.map_x(math_x), self.map_y(math_y)

    @classmethod
    def create_grid_cell(cls, row: int, col: int, num_rows: int, num_cols: int,
                         x_min: float, x_max: float, y_min: float, y_max: float,
                         canvas_width: float = 720, canvas_height: float = 405,
                         gap_x: float = 50, gap_y: float = 50,
                         margin_left: float = 60, margin_right: float = 40,
                         margin_top: float = 50, margin_bottom: float = 50):
        """
        Classmethod to divide a widescreen canvas into a structured grid of viewports.
        """
        grid_width = canvas_width - margin_left - margin_right
        grid_height = canvas_height - margin_top - margin_bottom
        
        cell_width = (grid_width - (num_cols - 1) * gap_x) / num_cols
        cell_height = (grid_height - (num_rows - 1) * gap_y) / num_rows
        
        cell_left = margin_left + col * (cell_width + gap_x)
        cell_top = margin_top + row * (cell_height + gap_y)
        
        cell_right = canvas_width - (cell_left + cell_width)
        cell_bottom = canvas_height - (cell_top + cell_height)
        
        return cls(
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
            canvas_width=canvas_width, canvas_height=canvas_height,
            margin_left=cell_left, margin_right=cell_right,
            margin_top=cell_top, margin_bottom=cell_bottom
        )


class AtomicDiagramGenerator(Canvas):
    """
    The Atomic Diagram Generator is the core artist engine. It subclasses the
    style guide Canvas to maintain full backward compatibility, SVG output capabilities,
    and output a beautifully formatted JSON layout that can be parsed and executed natively
    by the Google Slides API.
    """
    def __init__(self, width: float = 1000, height: float = 562.5, font_family: str = 'Ubuntu'):
        super().__init__(width=width, height=height, font_family=font_family)
        
    def save(self, filepath: str):
        """
        Saves grouped SVG to filepath and recursively flattens any nested SVGGroup
        elements into flat metadata commands in the structured JSON file.
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.render())
            
        try:
            json_filepath = filepath.replace(".svg", ".json")
            
            def flatten_elements(elements):
                flat = []
                for el in elements:
                    if hasattr(el, 'sub_elements') and el.sub_elements:
                        group_id = getattr(el, 'group_id', 'group_0')
                        child_ids = []
                        for child_idx, child in enumerate(el.sub_elements):
                            if hasattr(child, 'metadata') and child.metadata:
                                meta = dict(child.metadata)
                                child_id = f"el_{group_id}_{child_idx}_{meta.get('type', 'line')}"
                                meta['id'] = child_id
                                child_ids.append(child_id)
                                flat.append(meta)
                        flat.append({
                            "type": "group",
                            "id": group_id,
                            "childrenObjectIds": child_ids
                        })
                    elif hasattr(el, 'metadata') and el.metadata:
                        flat.append(el.metadata)
                return flat
                
            serialized_elements = flatten_elements(self.elements)
            
            payload = {
                "width": self.width,
                "height": self.height,
                "font_family": self.font_family,
                "elements": serialized_elements
            }
            with open(json_filepath, 'w', encoding='utf-8') as jf:
                json.dump(payload, jf, indent=2)
            print(f"[AtomicDiagramGenerator] Saved SVG to {filepath} and flattened structured JSON to {json_filepath}")
        except Exception as e:
            print(f"Error serializing generator canvas to JSON: {e}")
        
    def queue_line(self, x1: float, y1: float, x2: float, y2: float, stroke: str = COLORS['black'], stroke_width: float = 2.0, dasharray: str = 'none'):
        self.add(draw_line(x1, y1, x2, y2, stroke=stroke, stroke_width=stroke_width, dasharray=dasharray))
        
    def queue_arrow(self, x1: float, y1: float, x2: float, y2: float, stroke: str = COLORS['black'], stroke_width: float = 3.0):
        self.add(draw_arrow(x1, y1, x2, y2, stroke=stroke, stroke_width=stroke_width))
        
    def queue_rect(self, x: float, y: float, width: float, height: float, fill: str = 'none', stroke: str = COLORS['black'], stroke_width: float = 2.0, rx: float = 0, ry: float = 0, dasharray: str = 'none'):
        self.add(draw_rect(x, y, width, height, fill=fill, stroke=stroke, stroke_width=stroke_width, rx=rx, ry=ry, dasharray=dasharray))
        
    def queue_circle(self, cx: float, cy: float, r: float, fill: str = 'none', stroke: str = COLORS['black'], stroke_width: float = 2.0, dasharray: str = 'none'):
        self.add(draw_circle(cx, cy, r, fill=fill, stroke=stroke, stroke_width=stroke_width, dasharray=dasharray))
        
    def queue_text(self, x: float, y: float, text: str, font_size: float = 16, color: str = COLORS['black'], bold: bool = False, italic: bool = False, align: str = 'start', mask_bg: bool = False, width: float = None, height: float = None):
        element = draw_text(x, y, text, font_size=font_size, color=color, bold=bold, italic=italic, align=align, mask_bg=mask_bg)
        if width is None:
            if mask_bg:
                width = len(text) * font_size * 0.85 + 20
            else:
                # Highly generous default to prevent vertical wrapping in Google Slides
                width = max(len(text) * font_size * 1.5 + 40, 120)
        if height is None:
            height = font_size * 1.8
        element.metadata['width'] = width
        element.metadata['height'] = height
        self.add(element)

    # --- ADVANCED MATHEMATICAL GRAPH RENDERING METHODS ---

    def draw_grid_and_axes(self, viewport: Viewport, x_ticks: list[float], y_ticks: list[float], x_label: str = None, y_label: str = None, show_grid: bool = True, show_labels: bool = True, boundary_style: str = 'box', x_break: bool = False, y_break: bool = False):
        """
        Draws the gridlines, main axes, and the numeric/name labels.
        Groups all gridlines and axes lines into a unified 'axes_group'.
        """
        axes_elements = []

        px_min = viewport.map_x(viewport.x_min)
        px_max = viewport.map_x(viewport.x_max)
        py_min = viewport.map_y(viewport.y_min)  # bottom of plot (higher screen Y)
        py_max = viewport.map_y(viewport.y_max)  # top of plot (lower screen Y)
        
        # Determine if we should draw axis breaks
        do_x_break = x_break or (x_break is not False and (viewport.x_min > 0.1 or viewport.x_max < -0.1))
        do_y_break = y_break or (y_break is not False and (viewport.y_min > 0.1 or viewport.y_max < -0.1))

        # 1. Grid lines
        if show_grid:
            for x_val in x_ticks:
                px = viewport.map_x(x_val)
                # Skip gridlines at boundaries to avoid overlap with frame/axes
                if math.isclose(px, px_min) or math.isclose(px, px_max):
                    continue
                axes_elements.append(draw_line(px, py_min, px, py_max, stroke=COLORS['light_gray'], stroke_width=1.0, dasharray="4,4"))
                
            for y_val in y_ticks:
                py = viewport.map_y(y_val)
                if math.isclose(py, py_min) or math.isclose(py, py_max):
                    continue
                axes_elements.append(draw_line(px_min, py, px_max, py, stroke=COLORS['light_gray'], stroke_width=1.0, dasharray="4,4"))

        # Determine axes positions for labels and tick placements
        # For box layout, ticks are along the bottom/left edges of the box
        # For arrows layout, ticks are along the 0.0 axis lines
        y_axis_pos = 0.0 if (viewport.y_min <= 0.0 <= viewport.y_max and boundary_style == 'arrows') else viewport.y_min
        x_axis_pos = 0.0 if (viewport.x_min <= 0.0 <= viewport.x_max and boundary_style == 'arrows') else viewport.x_min

        # 2. Main Boundary Frame / Axes lines
        if boundary_style == 'box':
            # Bottom edge: (px_min, py_min) to (px_max, py_min)
            if do_x_break:
                px_break = px_min + 30.0
                axes_elements.append(draw_line(px_min, py_min, px_break - 10, py_min, stroke=COLORS['black'], stroke_width=2.0))
                # Zig-zag wave crossing the horizontal line
                axes_elements.append(draw_line(px_break - 10, py_min, px_break - 5, py_min - 6, stroke=COLORS['black'], stroke_width=2.0))
                axes_elements.append(draw_line(px_break - 5, py_min - 6, px_break, py_min + 6, stroke=COLORS['black'], stroke_width=2.0))
                axes_elements.append(draw_line(px_break, py_min + 6, px_break + 5, py_min - 6, stroke=COLORS['black'], stroke_width=2.0))
                axes_elements.append(draw_line(px_break + 5, py_min - 6, px_break + 10, py_min, stroke=COLORS['black'], stroke_width=2.0))
                axes_elements.append(draw_line(px_break + 10, py_min, px_max, py_min, stroke=COLORS['black'], stroke_width=2.0))
            else:
                axes_elements.append(draw_line(px_min, py_min, px_max, py_min, stroke=COLORS['black'], stroke_width=2.0))
                
            # Left edge: (px_min, py_min) to (px_min, py_max)
            if do_y_break:
                py_break = py_min - 30.0
                axes_elements.append(draw_line(px_min, py_min, px_min, py_break + 10, stroke=COLORS['black'], stroke_width=2.0))
                # Zig-zag wave crossing the vertical line
                axes_elements.append(draw_line(px_min, py_break + 10, px_min - 6, py_break + 5, stroke=COLORS['black'], stroke_width=2.0))
                axes_elements.append(draw_line(px_min - 6, py_break + 5, px_min + 6, py_break, stroke=COLORS['black'], stroke_width=2.0))
                axes_elements.append(draw_line(px_min + 6, py_break, px_min - 6, py_break - 5, stroke=COLORS['black'], stroke_width=2.0))
                axes_elements.append(draw_line(px_min - 6, py_break - 5, px_min, py_break - 10, stroke=COLORS['black'], stroke_width=2.0))
                axes_elements.append(draw_line(px_min, py_break - 10, px_min, py_max, stroke=COLORS['black'], stroke_width=2.0))
            else:
                axes_elements.append(draw_line(px_min, py_min, px_min, py_max, stroke=COLORS['black'], stroke_width=2.0))
                
            # Top and Right edges of box
            axes_elements.append(draw_line(px_min, py_max, px_max, py_max, stroke=COLORS['black'], stroke_width=2.0))
            axes_elements.append(draw_line(px_max, py_min, px_max, py_max, stroke=COLORS['black'], stroke_width=2.0))

        elif boundary_style == 'arrows':
            py_axis = viewport.map_y(y_axis_pos)
            px_axis = viewport.map_x(x_axis_pos)
            
            # Draw X-axis
            if do_x_break:
                px_break = px_min + 30.0
                axes_elements.append(draw_line(px_min, py_axis, px_break - 10, py_axis, stroke=COLORS['black'], stroke_width=2.5))
                # Zig-zag wave crossing the horizontal line
                axes_elements.append(draw_line(px_break - 10, py_axis, px_break - 5, py_axis - 6, stroke=COLORS['black'], stroke_width=2.5))
                axes_elements.append(draw_line(px_break - 5, py_axis - 6, px_break, py_axis + 6, stroke=COLORS['black'], stroke_width=2.5))
                axes_elements.append(draw_line(px_break, py_axis + 6, px_break + 5, py_axis - 6, stroke=COLORS['black'], stroke_width=2.5))
                axes_elements.append(draw_line(px_break + 5, py_axis - 6, px_break + 10, py_axis, stroke=COLORS['black'], stroke_width=2.5))
                axes_elements.append(draw_arrow(px_break + 10, py_axis, px_max + 15, py_axis, stroke=COLORS['black'], stroke_width=2.5))
            else:
                axes_elements.append(draw_arrow(px_min, py_axis, px_max + 15, py_axis, stroke=COLORS['black'], stroke_width=2.5))
                
            # Draw Y-axis
            if do_y_break:
                py_break = py_min - 30.0
                axes_elements.append(draw_line(px_axis, py_min, px_axis, py_break + 10, stroke=COLORS['black'], stroke_width=2.5))
                # Zig-zag wave crossing the vertical line
                axes_elements.append(draw_line(px_axis, py_break + 10, px_axis - 6, py_break + 5, stroke=COLORS['black'], stroke_width=2.5))
                axes_elements.append(draw_line(px_axis - 6, py_break + 5, px_axis + 6, py_break, stroke=COLORS['black'], stroke_width=2.5))
                axes_elements.append(draw_line(px_axis + 6, py_break, px_axis - 6, py_break - 5, stroke=COLORS['black'], stroke_width=2.5))
                axes_elements.append(draw_line(px_axis - 6, py_break - 5, px_axis, py_break - 10, stroke=COLORS['black'], stroke_width=2.5))
                axes_elements.append(draw_arrow(px_axis, py_break - 10, px_axis, py_max - 15, stroke=COLORS['black'], stroke_width=2.5))
            else:
                axes_elements.append(draw_arrow(px_axis, py_min, px_axis, py_max - 15, stroke=COLORS['black'], stroke_width=2.5))

        # Add the unified axes_group to the canvas elements
        if axes_elements:
            self.add(SVGGroup("axes_group", axes_elements))
        
        # 3. Tick Labels (numbers) and Axis Labels (names)
        if show_labels:
            # Origin label (0)
            if viewport.x_min <= 0.0 <= viewport.x_max and viewport.y_min <= 0.0 <= viewport.y_max and not do_x_break and not do_y_break:
                ox = viewport.map_x(0.0) - 10
                oy = viewport.map_y(0.0) + 12
                self.queue_text(ox, oy, "0", font_size=12, color=COLORS['dark_gray'], align='right', mask_bg=True)
                
            # X-tick numbers
            for x_val in x_ticks:
                if x_val == 0.0 and not do_x_break:
                    continue
                px = viewport.map_x(x_val)
                py = viewport.map_y(y_axis_pos) + 16
                lbl = f"{int(x_val)}" if x_val.is_integer() else f"{x_val:.1f}"
                self.queue_text(px, py, lbl, font_size=12, color=COLORS['dark_gray'], align='center', mask_bg=True)
                
            # Y-tick numbers
            for y_val in y_ticks:
                if y_val == 0.0 and not do_y_break:
                    continue
                py = viewport.map_y(y_val)
                px = viewport.map_x(x_axis_pos) - 10
                lbl = f"{int(y_val)}" if y_val.is_integer() else f"{y_val:.1f}"
                self.queue_text(px, py, lbl, font_size=12, color=COLORS['dark_gray'], align='right', mask_bg=True)
                
            # X-axis name label (e.g., "x")
            if x_label:
                lx = viewport.map_x(viewport.x_max) + 25
                ly = viewport.map_y(y_axis_pos)
                self.queue_text(lx, ly, x_label, font_size=14, color=COLORS['black'], bold=True, align='left')
                
            # Y-axis name label (e.g., "y")
            if y_label:
                lx = viewport.map_x(x_axis_pos)
                ly = viewport.map_y(viewport.y_max) - 28
                self.queue_text(lx, ly, y_label, font_size=14, color=COLORS['black'], bold=True, align='center')

    def draw_math_function(self, viewport: Viewport, func, x_start: float = None, x_end: float = None, stroke: str = COLORS['blue_primary'], stroke_width: float = 3.0, dasharray: str = 'none', steps: int = 200, group_id: str = "sinus_curve"):
        """
        Discretizes a mathematical function into segments and draws them.
        Wraps them in an SVGGroup if group_id is specified.
        """
        if x_start is None: x_start = viewport.x_min
        if x_end is None: x_end = viewport.x_max
        
        points = []
        step_size = (x_end - x_start) / steps
        for i in range(steps + 1):
            x = x_start + i * step_size
            try:
                y = func(x)
                if math.isfinite(y):
                    points.append((x, y))
            except (ValueError, ZeroDivisionError, OverflowError):
                pass
                
        # Draw line segments
        y_margin = viewport.y_range * 1.0
        y_lower = viewport.y_min - y_margin
        y_upper = viewport.y_max + y_margin
        
        segments = []
        for i in range(len(points) - 1):
            pt1 = points[i]
            pt2 = points[i+1]
            
            # Clip extreme values
            if y_lower <= pt1[1] <= y_upper and y_lower <= pt2[1] <= y_upper:
                px1, py1 = viewport.map_coords(pt1[0], pt1[1])
                px2, py2 = viewport.map_coords(pt2[0], pt2[1])
                segments.append(draw_line(px1, py1, px2, py2, stroke=stroke, stroke_width=stroke_width, dasharray=dasharray))
                
        if group_id and segments:
            self.add(SVGGroup(group_id, segments))
        else:
            for s in segments:
                self.add(s)

    def draw_parametric_function(self, viewport: Viewport, x_func, y_func, t_start: float, t_end: float, stroke: str = COLORS['blue_primary'], stroke_width: float = 3.0, dasharray: str = 'none', steps: int = 200, group_id: str = "parametric_curve"):
        """
        Discretizes a parametric function into segments and draws them.
        Wraps them in an SVGGroup if group_id is specified.
        """
        points = []
        step_size = (t_end - t_start) / steps
        for i in range(steps + 1):
            t = t_start + i * step_size
            try:
                x = x_func(t)
                y = y_func(t)
                if math.isfinite(x) and math.isfinite(y):
                    points.append((x, y))
            except (ValueError, ZeroDivisionError, OverflowError):
                pass
                
        # Draw line segments
        x_margin = viewport.x_range * 1.0
        x_lower = viewport.x_min - x_margin
        x_upper = viewport.x_max + x_margin
        
        y_margin = viewport.y_range * 1.0
        y_lower = viewport.y_min - y_margin
        y_upper = viewport.y_max + y_margin
        
        segments = []
        for i in range(len(points) - 1):
            pt1 = points[i]
            pt2 = points[i+1]
            
            # Clip values to viewport boundaries
            if (x_lower <= pt1[0] <= x_upper and y_lower <= pt1[1] <= y_upper and
                x_lower <= pt2[0] <= x_upper and y_lower <= pt2[1] <= y_upper):
                px1, py1 = viewport.map_coords(pt1[0], pt1[1])
                px2, py2 = viewport.map_coords(pt2[0], pt2[1])
                segments.append(draw_line(px1, py1, px2, py2, stroke=stroke, stroke_width=stroke_width, dasharray=dasharray))
                
        if group_id and segments:
            self.add(SVGGroup(group_id, segments))
        else:
            for s in segments:
                self.add(s)

    def draw_piecewise_line(self, viewport: Viewport, coords: list[tuple[float, float]], stroke: str = COLORS['black'], stroke_width: float = 3.0, dasharray: str = 'none'):
        """
        Draws continuous line segments between mathematical coordinates.
        """
        for i in range(len(coords) - 1):
            pt1 = coords[i]
            pt2 = coords[i+1]
            px1, py1 = viewport.map_coords(pt1[0], pt1[1])
            px2, py2 = viewport.map_coords(pt2[0], pt2[1])
            self.queue_line(px1, py1, px2, py2, stroke=stroke, stroke_width=stroke_width, dasharray=dasharray)

    def draw_hatch_area(self, viewport: Viewport, func_top, func_bottom, x_start: float, x_end: float, stroke: str = COLORS['blue_bg'], stroke_width: float = 1.0, step_pt: float = 4.0):
        """
        Shades the region between top and bottom functions using highly educational vertical hatching lines.
        Spacing of lines is computed based on screen space PT to ensure visually uniform density.
        """
        math_step = step_pt * (viewport.x_range / viewport.plot_width)
        if math_step <= 0:
            return
            
        x = x_start
        while x <= x_end + 1e-9:
            try:
                y_top = func_top(x) if callable(func_top) else float(func_top)
                y_bottom = func_bottom(x) if callable(func_bottom) else float(func_bottom)
                
                if math.isfinite(y_top) and math.isfinite(y_bottom):
                    px, py_top = viewport.map_coords(x, y_top)
                    _, py_bottom = viewport.map_coords(x, y_bottom)
                    self.queue_line(px, py_top, px, py_bottom, stroke=stroke, stroke_width=stroke_width)
            except Exception:
                pass
            x += math_step

    def draw_point(self, viewport: Viewport, x: float, y: float, label: str = None, label_offset_pt: tuple[float, float] = (10, -10), color: str = COLORS['black'], dot_size_pt: float = 8.0, font_size: float = 14, bold: bool = True, italic: bool = False):
        """
        Draws a key coordinate point marker with label offset.
        """
        px, py = viewport.map_coords(x, y)
        
        # Use our newly added native circle element
        self.queue_circle(px, py, dot_size_pt / 2.0, fill=color, stroke='none')
        
        if label:
            lx = px + label_offset_pt[0]
            ly = py + label_offset_pt[1]
            align = 'center'
            if label_offset_pt[0] > 2:
                align = 'left'
            elif label_offset_pt[0] < -2:
                align = 'right'
                
            self.queue_text(lx, ly, label, font_size=font_size, color=color, bold=bold, italic=italic, align=align)

    def queue_double_arrow(self, x1: float, y1: float, x2: float, y2: float, stroke: str = COLORS['black'], stroke_width: float = 2.0):
        """
        Draws horizontal or vertical double-headed arrow using two standard arrows going in opposite directions.
        """
        self.queue_arrow(x1, y1, x2, y2, stroke=stroke, stroke_width=stroke_width)
        self.queue_arrow(x2, y2, x1, y1, stroke=stroke, stroke_width=stroke_width)

    def draw_phase_marker(self, viewport: Viewport, x_start: float, x_end: float, y_val: float, label: str, stroke: str = COLORS['black'], stroke_width: float = 2.0, font_size: float = 14):
        """
        Draws horizontal double arrows from x_start to x_end at y_val, with a text label,
        and vertical dashed boundary lines extending down to the bottom of the viewport.
        """
        px_start, py_arrow = viewport.map_coords(x_start, y_val)
        px_end, _ = viewport.map_coords(x_end, y_val)
        
        self.queue_double_arrow(px_start, py_arrow, px_end, py_arrow, stroke=stroke, stroke_width=stroke_width)
        
        px_mid = (px_start + px_end) / 2.0
        self.queue_text(px_mid, py_arrow - 15, label, font_size=font_size, color=stroke, bold=True, align='center', mask_bg=True)
        
        py_bottom = viewport.map_y(viewport.y_min)
        self.queue_line(px_start, py_arrow + 5, px_start, py_bottom, stroke=COLORS['mid_gray'], stroke_width=1.0, dasharray="4,4")
        self.queue_line(px_end, py_arrow + 5, px_end, py_bottom, stroke=COLORS['mid_gray'], stroke_width=1.0, dasharray="4,4")

    def draw_legend(self, x: float, y: float, items: list[tuple[str, str]], width: float = 150, font_size: float = 14, stroke: str = COLORS['black'], fill: str = COLORS['white']):
        """
        Draws a custom legend box at canvas coordinates (x, y) containing color keys and labels.
        items: list of (label_text, color_hex)
        """
        row_height = font_size * 2.0
        box_height = len(items) * row_height + 15
        
        self.queue_rect(x, y, width, box_height, fill=fill, stroke=stroke, stroke_width=1.5, rx=4, ry=4)
        
        for i, (label, color) in enumerate(items):
            iy = y + 15 + i * row_height + font_size / 2.0
            self.queue_rect(x + 12, iy - 6, 12, 12, fill=color, stroke='#444444', stroke_width=1.0)
            self.queue_text(x + 32, iy, label, font_size=font_size, color=COLORS['black'], align='left')

    def draw_latex(self, latex_str: str, x: float, y: float, font_size: float = 16, color: str = COLORS['black'], align: str = 'center', group_id: str = None, mask_bg: bool = False):
        """
        Compiles a LaTeX expression to SVG using pdflatex and dvisvgm,
        converts the SVG to a transparent PNG using Inkscape,
        and adds it as an image element for perfect vector/pixel quality on the slide.
        
        If LaTeX compilation or conversion is unavailable, falls back to regular text.
        """
        if not group_id:
            group_id = f"latex_formula_{len(self.elements)}"
            
        preamble_parts = []
        for name, hex_code in COLORS.items():
            preamble_parts.append(f"\\definecolor{{{name}}}{{HTML}}{{{hex_code.lstrip('#').upper()}}}")
            
        extra_preamble = "\n".join(preamble_parts)
        
        # Build color override command for text color
        color_hex = color.lstrip('#')
        if len(color_hex) == 3:
            color_hex = "".join([c*2 for c in color_hex])
        
        latex_with_color = f"\\textcolor[HTML]{{{color_hex.upper()}}}{{{latex_str}}}"
        
        tex_template = r"""\documentclass[preview,border=4pt]{standalone}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage[utf8]{inputenx}
\usepackage{xcolor}
\usepackage{sfmath}
\renewcommand{\familydefault}{\sfdefault}

%s

\begin{document}
\begin{preview}
\boldmath
$%s$
\end{preview}
\end{document}
""" % (extra_preamble, latex_with_color)

        svg_content = None
        local_png_path = os.path.join(tempfile.gettempdir(), f"latex_{group_id}.png")
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tex_path = os.path.join(tmpdir, "formula.tex")
                with open(tex_path, "w", encoding="utf-8") as f:
                    f.write(tex_template)
                
                # 1. Compile LaTeX to DVI/PDF
                cmd_pdf = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "formula.tex"]
                subprocess.run(cmd_pdf, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                
                pdf_path = os.path.join(tmpdir, "formula.pdf")
                svg_path = os.path.join(tmpdir, "formula.svg")
                
                # 2. Convert PDF to SVG
                cmd_svg = ["dvisvgm", "--pdf", "--no-fonts", "formula.pdf", "-o", "formula.svg"]
                subprocess.run(cmd_svg, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                
                with open(svg_path, "r", encoding="utf-8") as f:
                    svg_content = f.read()
                    
                # 3. Convert SVG to transparent PNG
                cmd_png = [
                    "inkscape",
                    "--export-filename=" + os.path.abspath(local_png_path),
                    "--export-area-drawing",
                    "--export-background-opacity=0",
                    "--export-dpi=300",
                    svg_path
                ]
                subprocess.run(cmd_png, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        except subprocess.CalledProcessError as e:
            stderr_msg = e.stderr or ""
            if isinstance(stderr_msg, bytes):
                stderr_msg = stderr_msg.decode('utf-8', errors='ignore')
            logger.error(f"[draw_latex] Subprocess failed! Command: {e.cmd}, Code: {e.returncode}, Error:\n{stderr_msg}")
            print(f"[AtomicDiagramGenerator] LaTeX/Inkscape compilation failed: {e}. Falling back to normal text.")
            self.queue_text(x, y, latex_str, font_size=font_size, color=color, align=align, mask_bg=mask_bg)
            return
        except Exception as e:
            logger.error(f"[draw_latex] LaTeX/Inkscape compilation failed with unexpected error: {e}", exc_info=True)
            print(f"[AtomicDiagramGenerator] LaTeX/Inkscape compilation failed: {e}. Falling back to normal text.")
            self.queue_text(x, y, latex_str, font_size=font_size, color=color, align=align, mask_bg=mask_bg)
            return
        if not svg_content or not os.path.exists(local_png_path):
            self.queue_text(x, y, latex_str, font_size=font_size, color=color, align=align)
            return

        try:
            # Parse the SVG to find the true tight bounding box of drawn paths
            root = ET.fromstring(svg_content)
            
            def strip_ns(el):
                if el.tag.startswith('{'):
                    el.tag = el.tag.split('}', 1)[1]
                for key in list(el.attrib.keys()):
                    if key.startswith('{'):
                        new_key = key.split('}', 1)[1]
                        el.attrib[new_key] = el.attrib.pop(key)
                for child in el:
                    strip_ns(child)
            strip_ns(root)
            
            path_elements = []
            traverse_elements(root, [1.0, 0.0, 0.0, 1.0, 0.0, 0.0], path_elements)
            
            all_pts_x = []
            all_pts_y = []
            for pe in path_elements:
                d_attr = pe['d']
                if not d_attr:
                    continue
                lines_list = discretize_path(d_attr, pe['matrix'])
                for pt1, pt2 in lines_list:
                    all_pts_x.extend([pt1[0], pt2[0]])
                    all_pts_y.extend([pt1[1], pt2[1]])
                    
            if not all_pts_x or not all_pts_y:
                # Fallback to standard SVG viewBox
                viewbox = root.attrib.get("viewBox", "0 0 100 20")
                parts = [float(val) for val in viewbox.split()]
                v_xmin, v_ymin, v_w, v_h = parts[0], parts[1], parts[2], parts[3]
                w_tight, h_tight = v_w, v_h
                cx, cy = v_xmin + v_w/2.0, v_ymin + v_h/2.0
            else:
                xmin, xmax = min(all_pts_x), max(all_pts_x)
                ymin, ymax = min(all_pts_y), max(all_pts_y)
                w_tight = xmax - xmin
                h_tight = ymax - ymin
                cx = (xmin + xmax) / 2.0
                cy = (ymin + ymax) / 2.0
                
            # Slide coordinates: scaled so the height of the cropped drawing area matches font_size!
            # Increase the height slightly to make LaTeX symbols appear clear and prominent!
            h_slide = font_size * 1.15
            scale_factor = h_slide / (h_tight if h_tight > 0 else 10.0)
            w_slide = w_tight * scale_factor
            
            if align == 'center':
                x_slide = x - w_slide / 2.0
                y_slide = y - h_slide / 2.0
            elif align in ('left', 'start'):
                x_slide = x
                y_slide = y - h_slide / 2.0
            elif align in ('right', 'end'):
                x_slide = x - w_slide
                y_slide = y - h_slide / 2.0
            else:
                x_slide = x - w_slide / 2.0
                y_slide = y - h_slide / 2.0
                
            # Add native SVGImage element
            if mask_bg:
                self.queue_rect(x_slide, y_slide, w_slide, h_slide, fill=COLORS['white'], stroke='none')
            self.add(SVGImage(local_png_path, x_slide, y_slide, w_slide, h_slide, group_id))
            print(f"[AtomicDiagramGenerator] Successfully compiled and placed tight LaTeX image '{latex_str}' at ({x_slide:.2f}, {y_slide:.2f}) size {w_slide:.2f}x{h_slide:.2f} PT.")
            
        except Exception as e:
            print(f"[AtomicDiagramGenerator] Error parsing LaTeX dimensions: {e}. Falling back to normal text.")
            self.queue_text(x, y, latex_str, font_size=font_size, color=color, align=align, mask_bg=mask_bg)


def tokenize_d(d_string):
    s = d_string.replace(',', ' ')
    s = re.sub(r'([A-Za-z])', r' \1 ', s)
    s = re.sub(r'(?<![eE\s])-', r' -', s)
    return s.split()


def parse_transform(transform_str):
    commands = re.findall(r'(\w+)\s*\(([^)]+)\)', transform_str)
    combined = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    
    for cmd, args_str in commands:
        args = [float(arg) for arg in re.split(r'[\s,]+', args_str.strip()) if arg]
        if not args:
            continue
            
        m = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        if cmd == 'translate':
            tx = args[0]
            ty = args[1] if len(args) > 1 else 0.0
            m = [1.0, 0.0, 0.0, 1.0, tx, ty]
        elif cmd == 'scale':
            sx = args[0]
            sy = args[1] if len(args) > 1 else sx
            m = [sx, 0.0, 0.0, sy, 0.0, 0.0]
        elif cmd == 'matrix':
            if len(args) == 6:
                m = args
                
        a1, b1, c1, d1, e1, f1 = combined
        a2, b2, c2, d2, e2, f2 = m
        combined = [
            a1*a2 + c1*b2,
            b1*a2 + d1*b2,
            a1*c2 + c1*d2,
            b1*c2 + d1*d2,
            a1*e2 + c1*f2 + e1,
            b1*e2 + d1*f2 + f1
        ]
        
    return combined


def traverse_elements(node, parent_matrix, path_elements):
    transform_str = node.attrib.get('transform', '')
    if transform_str:
        local_matrix = parse_transform(transform_str)
        a1, b1, c1, d1, e1, f1 = parent_matrix
        a2, b2, c2, d2, e2, f2 = local_matrix
        current_matrix = [
            a1*a2 + c1*b2,
            b1*a2 + d1*b2,
            a1*c2 + c1*d2,
            b1*c2 + d1*d2,
            a1*e2 + c1*f2 + e1,
            b1*e2 + d1*f2 + f1
        ]
    else:
        current_matrix = list(parent_matrix)
        
    tag = node.tag.split('}')[-1]
    if tag == 'path':
        d = node.attrib.get('d', '')
        fill = node.attrib.get('fill', '')
        stroke = node.attrib.get('stroke', '')
        stroke_width = node.attrib.get('stroke-width', '')
        path_elements.append({
            'd': d,
            'fill': fill,
            'stroke': stroke,
            'stroke_width': stroke_width,
            'matrix': current_matrix
        })
        
    for child in node:
        traverse_elements(child, current_matrix, path_elements)


def discretize_path(d_string, matrix):
    a, b, c_val, d_val, e, f = matrix
    def transform_pt(x, y):
        return a*x + c_val*y + e, b*x + d_val*y + f
        
    tokens = tokenize_d(d_string)
    lines = []
    i = 0
    cmd = None
    prev_cmd = None
    
    curr_x, curr_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0
    prev_cx, prev_cy = 0.0, 0.0
    
    while i < len(tokens):
        token = tokens[i]
        if token.isalpha() and len(token) == 1:
            prev_cmd = cmd
            cmd = token
            i += 1
            
        if cmd == 'M':
            curr_x = float(tokens[i])
            curr_y = float(tokens[i+1])
            start_x, start_y = curr_x, curr_y
            i += 2
            cmd = 'L'
        elif cmd == 'm':
            curr_x += float(tokens[i])
            curr_y += float(tokens[i+1])
            start_x, start_y = curr_x, curr_y
            i += 2
            cmd = 'l'
        elif cmd == 'L':
            next_x = float(tokens[i])
            next_y = float(tokens[i+1])
            lines.append((transform_pt(curr_x, curr_y), transform_pt(next_x, next_y)))
            curr_x, curr_y = next_x, next_y
            i += 2
        elif cmd == 'l':
            next_x = curr_x + float(tokens[i])
            next_y = curr_y + float(tokens[i+1])
            lines.append((transform_pt(curr_x, curr_y), transform_pt(next_x, next_y)))
            curr_x, curr_y = next_x, next_y
            i += 2
        elif cmd == 'H':
            next_x = float(tokens[i])
            lines.append((transform_pt(curr_x, curr_y), transform_pt(next_x, curr_y)))
            curr_x = next_x
            i += 1
        elif cmd == 'h':
            next_x = curr_x + float(tokens[i])
            lines.append((transform_pt(curr_x, curr_y), transform_pt(next_x, curr_y)))
            curr_x = next_x
            i += 1
        elif cmd == 'V':
            next_y = float(tokens[i])
            lines.append((transform_pt(curr_x, curr_y), transform_pt(curr_x, next_y)))
            curr_y = next_y
            i += 1
        elif cmd == 'v':
            next_y = curr_y + float(tokens[i])
            lines.append((transform_pt(curr_x, curr_y), transform_pt(curr_x, next_y)))
            curr_y = next_y
            i += 1
        elif cmd == 'C':
            x1, y1 = float(tokens[i]), float(tokens[i+1])
            x2, y2 = float(tokens[i+2]), float(tokens[i+3])
            x3, y3 = float(tokens[i+4]), float(tokens[i+5])
            steps = 3
            prev_pt_x, prev_pt_y = curr_x, curr_y
            for s in range(1, steps + 1):
                t = s / steps
                bx = (1-t)**3 * curr_x + 3*(1-t)**2*t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x3
                by = (1-t)**3 * curr_y + 3*(1-t)**2*t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y3
                lines.append((transform_pt(prev_pt_x, prev_pt_y), transform_pt(bx, by)))
                prev_pt_x, prev_pt_y = bx, by
            curr_x, curr_y = x3, y3
            prev_cx, prev_cy = x2, y2
            i += 6
        elif cmd == 'c':
            x1 = curr_x + float(tokens[i])
            y1 = curr_y + float(tokens[i+1])
            x2 = curr_x + float(tokens[i+2])
            y2 = curr_y + float(tokens[i+3])
            x3 = curr_x + float(tokens[i+4])
            y3 = curr_y + float(tokens[i+5])
            steps = 3
            prev_pt_x, prev_pt_y = curr_x, curr_y
            for s in range(1, steps + 1):
                t = s / steps
                bx = (1-t)**3 * curr_x + 3*(1-t)**2*t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x3
                by = (1-t)**3 * curr_y + 3*(1-t)**2*t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y3
                lines.append((transform_pt(prev_pt_x, prev_pt_y), transform_pt(bx, by)))
                prev_pt_x, prev_pt_y = bx, by
            curr_x, curr_y = x3, y3
            prev_cx, prev_cy = x2, y2
            i += 6
        elif cmd == 'S':
            x2, y2 = float(tokens[i]), float(tokens[i+1])
            x3, y3 = float(tokens[i+2]), float(tokens[i+3])
            if prev_cmd in ('C', 'c', 'S', 's'):
                x1 = 2.0 * curr_x - prev_cx
                y1 = 2.0 * curr_y - prev_cy
            else:
                x1, y1 = curr_x, curr_y
            steps = 3
            prev_pt_x, prev_pt_y = curr_x, curr_y
            for s_step in range(1, steps + 1):
                t = s_step / steps
                bx = (1-t)**3 * curr_x + 3*(1-t)**2*t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x3
                by = (1-t)**3 * curr_y + 3*(1-t)**2*t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y3
                lines.append((transform_pt(prev_pt_x, prev_pt_y), transform_pt(bx, by)))
                prev_pt_x, prev_pt_y = bx, by
            curr_x, curr_y = x3, y3
            prev_cx, prev_cy = x2, y2
            i += 4
        elif cmd == 's':
            x2 = curr_x + float(tokens[i])
            y2 = curr_y + float(tokens[i+1])
            x3 = curr_x + float(tokens[i+2])
            y3 = curr_y + float(tokens[i+3])
            if prev_cmd in ('C', 'c', 'S', 's'):
                x1 = 2.0 * curr_x - prev_cx
                y1 = 2.0 * curr_y - prev_cy
            else:
                x1, y1 = curr_x, curr_y
            steps = 3
            prev_pt_x, prev_pt_y = curr_x, curr_y
            for s_step in range(1, steps + 1):
                t = s_step / steps
                bx = (1-t)**3 * curr_x + 3*(1-t)**2*t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x3
                by = (1-t)**3 * curr_y + 3*(1-t)**2*t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y3
                lines.append((transform_pt(prev_pt_x, prev_pt_y), transform_pt(bx, by)))
                prev_pt_x, prev_pt_y = bx, by
            curr_x, curr_y = x3, y3
            prev_cx, prev_cy = x2, y2
            i += 4
        elif cmd in ('Z', 'z'):
            if start_x is not None and (curr_x != start_x or curr_y != start_y):
                lines.append((transform_pt(curr_x, curr_y), transform_pt(start_x, start_y)))
                curr_x, curr_y = start_x, start_y
            i += 1
        else:
            i += 1
            
    return lines


def generate_ticks(start: float, end: float, step: float) -> list[float]:
    """
    Helper function to generate clean tick coordinates at exact step increments, aligned with the step.
    """
    if step <= 0:
        return []
    ticks = []
    first_tick = math.ceil(start / step) * step
    val = first_tick
    eps = step * 1e-6
    while val <= end + eps:
        if abs(val) < eps:
            val = 0.0
        ticks.append(val)
        val += step
    return ticks


def numerical_derivative(func, x: float, h: float = 1e-5) -> float:
    """
    Computes numerical derivative using standard central difference.
    """
    return (func(x + h) - func(x - h)) / (2.0 * h)


def compile_latex_to_png(latex_str: str, font_size: float, color: str, align: str = 'center', group_id: str = None) -> dict:
    """
    Compiles a LaTeX expression to a transparent PNG and returns metadata about its placement.
    Returns a dict with keys:
      'local_path': str
      'width': float
      'height': float
      'x_offset': float
      'y_offset': float
    Or None if compilation fails.
    """
    import uuid
    if not group_id:
        group_id = f"latex_gslides_{uuid.uuid4().hex[:8]}"
        
    preamble_parts = []
    for name, hex_code in COLORS.items():
        preamble_parts.append(f"\\definecolor{{{name}}}{{HTML}}{{{hex_code.lstrip('#').upper()}}}")
        
    extra_preamble = "\n".join(preamble_parts)
    
    color_hex = color.lstrip('#')
    if len(color_hex) == 3:
        color_hex = "".join([c*2 for c in color_hex])
    
    latex_with_color = f"\\textcolor[HTML]{{{color_hex.upper()}}}{{{latex_str}}}"
    
    tex_template = r"""\documentclass[preview,border=4pt]{standalone}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage[utf8]{inputenx}
\usepackage{xcolor}
\usepackage{sfmath}
\renewcommand{\familydefault}{\sfdefault}

%s

\begin{document}
\begin{preview}
\boldmath
$%s$
\end{preview}
\end{document}
""" % (extra_preamble, latex_with_color)

    local_png_path = os.path.join(tempfile.gettempdir(), f"latex_{group_id}.png")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "formula.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(tex_template)
            
            # 1. Compile LaTeX to DVI/PDF
            cmd_pdf = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "formula.tex"]
            subprocess.run(cmd_pdf, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            
            pdf_path = os.path.join(tmpdir, "formula.pdf")
            svg_path = os.path.join(tmpdir, "formula.svg")
            
            # 2. Convert PDF to SVG
            cmd_svg = ["dvisvgm", "--pdf", "--no-fonts", "formula.pdf", "-o", "formula.svg"]
            subprocess.run(cmd_svg, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
                
            # 3. Convert SVG to transparent PNG
            cmd_png = [
                "inkscape",
                "--export-filename=" + os.path.abspath(local_png_path),
                "--export-area-drawing",
                "--export-background-opacity=0",
                "--export-dpi=300",
                svg_path
            ]
            subprocess.run(cmd_png, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            
            root = ET.fromstring(svg_content)
            
            def strip_ns(el):
                if el.tag.startswith('{'):
                    el.tag = el.tag.split('}', 1)[1]
                for key in list(el.attrib.keys()):
                    if key.startswith('{'):
                        new_key = key.split('}', 1)[1]
                        el.attrib[new_key] = el.attrib.pop(key)
                for child in el:
                    strip_ns(child)
            strip_ns(root)
            
            path_elements = []
            traverse_elements(root, [1.0, 0.0, 0.0, 1.0, 0.0, 0.0], path_elements)
            
            all_pts_x = []
            all_pts_y = []
            for pe in path_elements:
                d_attr = pe['d']
                if not d_attr:
                    continue
                lines_list = discretize_path(d_attr, pe['matrix'])
                for pt1, pt2 in lines_list:
                    all_pts_x.extend([pt1[0], pt2[0]])
                    all_pts_y.extend([pt1[1], pt2[1]])
                    
            if not all_pts_x or not all_pts_y:
                viewbox = root.attrib.get("viewBox", "0 0 100 20")
                parts = [float(val) for val in viewbox.split()]
                v_xmin, v_ymin, v_w, v_h = parts[0], parts[1], parts[2], parts[3]
                w_tight, h_tight = v_w, v_h
            else:
                xmin, xmax = min(all_pts_x), max(all_pts_x)
                ymin, ymax = min(all_pts_y), max(all_pts_y)
                w_tight = xmax - xmin
                h_tight = ymax - ymin
                
            h_slide = font_size * 1.15
            scale_factor = h_slide / (h_tight if h_tight > 0 else 10.0)
            w_slide = w_tight * scale_factor
            
            if align == 'center':
                x_offset = - w_slide / 2.0
            elif align in ('left', 'start'):
                x_offset = 0.0
            elif align in ('right', 'end'):
                x_offset = - w_slide
            else:
                x_offset = - w_slide / 2.0
                
            y_offset = - h_slide / 2.0
            
            return {
                'local_path': local_png_path,
                'width': w_slide,
                'height': h_slide,
                'x_offset': x_offset,
                'y_offset': y_offset
            }
            
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr or ""
        if isinstance(stderr_msg, bytes):
            stderr_msg = stderr_msg.decode('utf-8', errors='ignore')
        logger.error(f"[compile_latex_to_png] Subprocess failed! Command: {e.cmd}, Code: {e.returncode}, Error:\n{stderr_msg}")
        print(f"[compile_latex_to_png] LaTeX/Inkscape compilation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"[compile_latex_to_png] LaTeX/Inkscape compilation failed with unexpected error: {e}", exc_info=True)
        print(f"[compile_latex_to_png] LaTeX/Inkscape compilation failed: {e}")
        return None
