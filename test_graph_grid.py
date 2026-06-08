import os
import math
import json
from graph_engine import Viewport, AtomicDiagramGenerator
from gslides_uploader import GoogleSlidesUploader, COLORS

def draw_cell_graph(generator, viewport, x_ticks, y_ticks, x_label, y_label, title_text=None):
    # Map viewport boundary coordinates in PT
    px_min, py_max = viewport.map_coords(viewport.x_min, viewport.y_max)
    px_max, py_min = viewport.map_coords(viewport.x_max, viewport.y_min)
    
    # 1. Draw solid thin black enclosing boundary frame
    generator.queue_rect(px_min, py_max, px_max - px_min, py_min - py_max, stroke='#444444', stroke_width=1.5, fill='none')
    
    # 2. Draw vertical grid lines
    for xv in x_ticks:
        if xv == viewport.x_min or xv == viewport.x_max:
            continue
        px = viewport.map_x(xv)
        generator.queue_line(px, py_max, px, py_min, stroke='#eeeeee', stroke_width=1.0, dasharray="3,3")
        
    # 3. Draw horizontal grid lines
    for yv in y_ticks:
        if yv == viewport.y_min or yv == viewport.y_max:
            continue
        py = viewport.map_y(yv)
        generator.queue_line(px_min, py, px_max, py, stroke='#eeeeee', stroke_width=1.0, dasharray="3,3")
        
    # 4. Draw X-axis tick labels
    for xv in x_ticks:
        px = viewport.map_x(xv)
        py_lbl = py_min + 12
        generator.queue_text(px, py_lbl, str(int(xv)), font_size=10, color='#666666', align='center')
        
    # 5. Draw Y-axis tick labels
    for yv in y_ticks:
        py = viewport.map_y(yv)
        px_lbl = px_min - 8
        generator.queue_text(px_lbl, py, str(int(yv)), font_size=10, color='#666666', align='right')
        
    # 6. Draw Axis Names (e.g. x, t)
    # X-axis label: e.g. t (s) -> t is bold italic, (s) is regular
    generator.queue_text(px_max + 10, py_min, x_label, font_size=11, color='#000000', bold=True, italic=True, align='left', width=20, height=20)
    
    # Y-axis label: e.g. x (m) -> x is bold italic, (m) is regular
    generator.queue_text(px_min, py_max - 12, y_label, font_size=11, color='#000000', bold=True, italic=True, align='center', width=30, height=20)
    
    # 7. Draw cell title
    if title_text:
        generator.queue_text((px_min + px_max)/2.0, py_max - 15, title_text, font_size=11, color='#0b5394', bold=True, align='center')


def main():
    print("Generating 2x3 Grid of vt and xt graphs (Image 5)...")
    
    canvas_w = 720
    canvas_h = 405
    
    generator = AtomicDiagramGenerator(width=canvas_w, height=canvas_h, font_family='Ubuntu')
    
    # Draw a grand presentation slide header
    generator.queue_text(30, 35, "Overzicht van Bewegingstypen (2x3 Grid)", font_size=20, color='#0b5394', bold=True, align='left')
    
    # Setup standard ticks for X and Y axes
    x_ticks = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    y_ticks = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    
    # --- COLUMN 0: Constant Velocity ---
    # Top: x(t) = t (linear increasing position)
    vp_c0_r0 = Viewport.create_grid_cell(row=0, col=0, num_rows=2, num_cols=3, x_min=0.0, x_max=5.0, y_min=0.0, y_max=5.0, margin_top=70, margin_bottom=40, gap_x=55, gap_y=55)
    draw_cell_graph(generator, vp_c0_r0, x_ticks, y_ticks, "t", "x", "Constant v: x(t)")
    generator.draw_math_function(vp_c0_r0, func=lambda t: t, stroke='#38761d', stroke_width=2.5, group_id="c0_r0")
    
    # Bottom: v(t) = 1 (constant horizontal velocity)
    vp_c0_r1 = Viewport.create_grid_cell(row=1, col=0, num_rows=2, num_cols=3, x_min=0.0, x_max=5.0, y_min=0.0, y_max=5.0, margin_top=70, margin_bottom=40, gap_x=55, gap_y=55)
    draw_cell_graph(generator, vp_c0_r1, x_ticks, y_ticks, "t", "v", "Constant v: v(t)")
    generator.draw_math_function(vp_c0_r1, func=lambda t: 1.0, stroke='#38761d', stroke_width=2.5, group_id="c0_r1")
    
    # --- COLUMN 1: Constant Positive Acceleration ---
    # Top: x(t) = 0.18 * t^2 (parabolic position)
    vp_c1_r0 = Viewport.create_grid_cell(row=0, col=1, num_rows=2, num_cols=3, x_min=0.0, x_max=5.0, y_min=0.0, y_max=5.0, margin_top=70, margin_bottom=40, gap_x=55, gap_y=55)
    draw_cell_graph(generator, vp_c1_r0, x_ticks, y_ticks, "t", "x", "Constant a: x(t)")
    generator.draw_math_function(vp_c1_r0, func=lambda t: 0.18 * t * t, stroke='#0b5394', stroke_width=2.5, group_id="c1_r0")
    
    # Bottom: v(t) = 0.36 * t (linear increasing velocity)
    vp_c1_r1 = Viewport.create_grid_cell(row=1, col=1, num_rows=2, num_cols=3, x_min=0.0, x_max=5.0, y_min=0.0, y_max=5.0, margin_top=70, margin_bottom=40, gap_x=55, gap_y=55)
    draw_cell_graph(generator, vp_c1_r1, x_ticks, y_ticks, "t", "v", "Constant a: v(t)")
    generator.draw_math_function(vp_c1_r1, func=lambda t: 0.36 * t, stroke='#0b5394', stroke_width=2.5, group_id="c1_r1")
    
    # --- COLUMN 2: Stationary (Rest) ---
    # Top: x(t) = 3 (constant position)
    vp_c2_r0 = Viewport.create_grid_cell(row=0, col=2, num_rows=2, num_cols=3, x_min=0.0, x_max=5.0, y_min=0.0, y_max=5.0, margin_top=70, margin_bottom=40, gap_x=55, gap_y=55)
    draw_cell_graph(generator, vp_c2_r0, x_ticks, y_ticks, "t", "x", "Stilstand: x(t)")
    generator.draw_math_function(vp_c2_r0, func=lambda t: 3.0, stroke='#980000', stroke_width=2.5, group_id="c2_r0")
    
    # Bottom: v(t) = 0 (zero velocity)
    vp_c2_r1 = Viewport.create_grid_cell(row=1, col=2, num_rows=2, num_cols=3, x_min=0.0, x_max=5.0, y_min=0.0, y_max=5.0, margin_top=70, margin_bottom=40, gap_x=55, gap_y=55)
    draw_cell_graph(generator, vp_c2_r1, x_ticks, y_ticks, "t", "v", "Stilstand: v(t)")
    generator.draw_math_function(vp_c2_r1, func=lambda t: 0.0, stroke='#980000', stroke_width=2.5, group_id="c2_r1")
    
    # Save local vector outputs
    output_base_path = "test_graph_grid"
    generator.save(f"{output_base_path}.svg")
    
    # Upload structured JSON to Google Slides
    json_path = f"{output_base_path}.json"
    if os.path.exists(json_path):
        print(f"Serialized JSON found. Loading: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            canvas_dict = json.load(f)
            
        creds_file = "credentials.json"
        if not os.path.exists(creds_file):
            creds_file = "service_account.json" if os.path.exists("service_account.json") else None
            
        try:
            uploader = GoogleSlidesUploader(credentials_path=creds_file)
            presentation_file = uploader.create_presentation_from_canvas_data(
                canvas_dict,
                name="2x3 Grid van vt en xt Grafieken (Widescreen)",
                folder_id=os.environ.get("DRIVE_FOLDER_ID")
            )
            print("\n" + "="*80)
            print("NATIVE GOOGLE SLIDES DIAGRAM CREATED SUCCESSFULLY!")
            print(f"Presentation Link: {presentation_file.get('webViewLink')}")
            print("="*80 + "\n")
        except Exception as e:
            print(f"\nFailed to upload diagram to Google Slides: {e}")
    else:
        print(f"Error: Could not find serialized JSON file: {json_path}")


if __name__ == "__main__":
    main()
