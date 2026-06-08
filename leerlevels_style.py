import math
import json

class SVGString(str):
    def __new__(cls, content, **metadata):
        obj = str.__new__(cls, content)
        obj.metadata = metadata
        return obj

class Canvas:
    def __init__(self, width=1000, height=562.5, font_family='Ubuntu'):
        self.width = width
        self.height = height
        self.font_family = font_family
        self.elements = []
        
    def add(self, element_svg):
        self.elements.append(element_svg)
        
    def render(self):
        svg_header = f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {self.width} {self.height}" width="{self.width}" height="{self.height}">'
        # Embed font dynamically based on self.font_family
        font_url_name = self.font_family.replace(" ", "+")
        defs = f'''
        <defs>
            <style>
                @import url('https://fonts.googleapis.com/css2?family={font_url_name}:ital,wght@0,300;0,400;0,500;0,700;1,400&display=swap');
                text {{ font-family: '{self.font_family}', sans-serif; }}
            </style>
        </defs>
        '''
        bg = f'<rect width="{self.width}" height="{self.height}" fill="#ffffff" />'
        
        rendered_elements = []
        for el in self.elements:
            rendered_elements.append(str(el))
            
        content = "\n".join(rendered_elements)
        svg_footer = "</svg>"
        return f"{svg_header}\n{defs}\n{bg}\n{content}\n{svg_footer}"
        
    def save(self, filepath):
        # Save SVG
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.render())
            
        # Also write structured JSON for Google Slides conversion
        try:
            json_filepath = filepath.replace(".svg", ".json")
            serialized_elements = []
            for el in self.elements:
                if hasattr(el, 'metadata') and el.metadata:
                    serialized_elements.append(el.metadata)
                # If there's no metadata, maybe it's raw text; ignore or log
                
            payload = {
                "width": self.width,
                "height": self.height,
                "font_family": self.font_family,
                "elements": serialized_elements
            }
            with open(json_filepath, 'w', encoding='utf-8') as jf:
                json.dump(payload, jf, indent=2)
            print(f"Canvas saved SVG to {filepath} and structured JSON to {json_filepath}")
        except Exception as e:
            print(f"Error serializing canvas to JSON: {e}")

# --- COLORS ---
COLORS = {
    'black': '#000000',
    'dark_gray': '#666666',
    'mid_gray': '#b7b7b7',
    'light_gray': '#cccccc',
    'bg_gray': '#efefef',
    'white': '#ffffff',
    
    'red_primary': '#980000',
    'red_bg': '#e6b8af',
    
    'blue_primary': '#0b5394',
    'blue_bg': '#cfe2f3',
    
    'green_primary': '#38761d',
    'green_bg': '#d9ead3',
    
    'yellow_primary': '#bf9000',
    'yellow_bg': '#fff2cc'
}

# --- PRIMITIVES ---

def draw_rect(x, y, width, height, fill='none', stroke=COLORS['black'], stroke_width=2.0, rx=0, ry=0, dasharray='none'):
    stroke_dash = f'stroke-dasharray="{dasharray}"' if dasharray != 'none' else ''
    content = f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" rx="{rx}" ry="{ry}" {stroke_dash} />'
    return SVGString(
        content,
        type='rect',
        x=x, y=y, width=width, height=height,
        fill=fill, stroke=stroke, stroke_width=stroke_width,
        rx=rx, ry=ry, dasharray=dasharray
    )

def draw_circle(cx, cy, r, fill='none', stroke=COLORS['black'], stroke_width=2.0, dasharray='none'):
    x = cx - r
    y = cy - r
    w = 2.0 * r
    h = 2.0 * r
    stroke_dash = f'stroke-dasharray="{dasharray}"' if dasharray != 'none' else ''
    content = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" {stroke_dash} />'
    return SVGString(
        content,
        type='circle',
        x=x, y=y, width=w, height=h,
        fill=fill, stroke=stroke, stroke_width=stroke_width,
        dasharray=dasharray
    )

def draw_line(x1, y1, x2, y2, stroke=COLORS['black'], stroke_width=2.0, dasharray='none'):
    stroke_dash = f'stroke-dasharray="{dasharray}"' if dasharray != 'none' else ''
    content = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{stroke_width}" {stroke_dash} />'
    return SVGString(
        content,
        type='line',
        x1=x1, y1=y1, x2=x2, y2=y2,
        stroke=stroke, stroke_width=stroke_width, dasharray=dasharray
    )

def draw_arrow(x1, y1, x2, y2, stroke=COLORS['black'], stroke_width=3.0):
    # Calculate arrowhead
    angle = math.atan2(y2 - y1, x2 - x1)
    head_len = 15
    head_angle = math.pi / 6
    
    ax1 = x2 - head_len * math.cos(angle - head_angle)
    ay1 = y2 - head_len * math.sin(angle - head_angle)
    
    ax2 = x2 - head_len * math.cos(angle + head_angle)
    ay2 = y2 - head_len * math.sin(angle + head_angle)
    
    line = draw_line(x1, y1, x2, y2, stroke, stroke_width)
    head = f'<polygon points="{x2},{y2} {ax1},{ay1} {ax2},{ay2}" fill="{stroke}" />'
    
    content = f'<g>{line}\n{head}</g>'
    return SVGString(
        content,
        type='arrow',
        x1=x1, y1=y1, x2=x2, y2=y2,
        stroke=stroke, stroke_width=stroke_width
    )

def draw_text(x, y, text, font_size=16, color=COLORS['black'], bold=False, italic=False, align='start', mask_bg=False):
    weight = "bold" if bold else "normal"
    style = "italic" if italic else "normal"
    anchor = "start" if align == 'left' else ("middle" if align == 'center' else "end")
    
    text_elem = f'<text x="{x}" y="{y}" font-size="{font_size}" fill="{color}" font-weight="{weight}" font-style="{style}" text-anchor="{anchor}" dominant-baseline="middle">{text}</text>'
    
    if mask_bg:
        # Approximate width based on character count
        approx_width = len(text) * font_size * 0.6
        bg_x = x - (approx_width/2 if align=='center' else (approx_width if align=='right' else 0)) - 4
        bg_y = y - font_size/2 - 4
        mask = draw_rect(bg_x, bg_y, approx_width + 8, font_size + 8, fill=COLORS['white'], stroke='none', rx=5, ry=5)
        content = f'<g>{mask}\n{text_elem}</g>'
        return SVGString(
            content,
            type='text',
            x=x, y=y, text=text, font_size=font_size, color=color,
            bold=bold, italic=italic, align=align, mask_bg=mask_bg
        )
    
    return SVGString(
        text_elem,
        type='text',
        x=x, y=y, text=text, font_size=font_size, color=color,
        bold=bold, italic=italic, align=align, mask_bg=mask_bg
    )

# --- HIGHER LEVEL ABSTRACTIONS ---

def draw_header(canvas, title):
    """Draws a standard header in the Leerlevels style."""
    canvas.add(draw_text(20, 40, title, font_size=24, color=COLORS['blue_primary'], bold=True, align='left'))

def draw_coordinate_system(canvas, x_start, y_start, x_end, y_end, grid_spacing=50):
    """Draws standard Leerlevels coordinate axes and grid."""
    # Grid
    for x in range(int(x_start), int(x_end), grid_spacing):
        canvas.add(draw_line(x, y_start, x, y_end, stroke=COLORS['dark_gray'], stroke_width=1.0, dasharray='4,3'))
    for y in range(int(y_end), int(y_start), grid_spacing):
        canvas.add(draw_line(x_start, y, x_end, y, stroke=COLORS['dark_gray'], stroke_width=1.0, dasharray='4,3'))
        
    # Axes
    canvas.add(draw_arrow(x_start, y_start, x_end + 20, y_start, stroke=COLORS['black'], stroke_width=3.0)) # X-axis
    canvas.add(draw_arrow(x_start, y_start, x_start, y_end - 20, stroke=COLORS['black'], stroke_width=3.0)) # Y-axis
