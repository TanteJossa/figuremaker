import os
import math
import json
from graph_engine import Viewport, AtomicDiagramGenerator
from gslides_uploader import GoogleSlidesUploader, COLORS

def main():
    print("Generating '(x,t)-grafiek met verschillende fases' (Image 3)...")
    
    # 1. Setup Canvas Dimensions (exact widescreen slide 16:9 bounds)
    canvas_w = 720
    canvas_h = 405
    
    # 2. Viewport margins and mathematical limits
    x_min, x_max = 0.0, 18.0
    y_min, y_max = 0.0, 14.0
    
    viewport = Viewport(
        x_min=x_min, x_max=x_max,
        y_min=y_min, y_max=y_max,
        canvas_width=canvas_w, canvas_height=canvas_h,
        margin_left=80, margin_right=40,
        margin_top=60, margin_bottom=50
    )
    
    # Create the generator with widescreen dimensions and standard font
    generator = AtomicDiagramGenerator(width=canvas_w, height=canvas_h, font_family='Ubuntu')
    
    # Grid dimensions in presentation points (PT)
    px_min = 80
    px_max = 680
    py_min = 355 # bottom edge of grid
    py_max = 50  # top edge of grid
    plot_w = 600
    plot_h = 305
    
    # 3. Draw dashed grid lines (spacing of 2 for X, and 2 for Y)
    x_grid_vals = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0]
    for xv in x_grid_vals:
        px = viewport.map_x(xv)
        generator.queue_line(px, py_max, px, py_min, stroke='#dddddd', stroke_width=1.0, dasharray="4,4")
        
    y_grid_vals = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
    for yv in y_grid_vals:
        py = viewport.map_y(yv)
        generator.queue_line(px_min, py, px_max, py, stroke='#dddddd', stroke_width=1.0, dasharray="4,4")
        
    # 4. Draw solid thick black enclosing boundary frame
    generator.queue_rect(px_min, py_max, plot_w, plot_h, stroke='#000000', stroke_width=3.0, fill='none')
    
    # 5. Draw X-axis tick labels (0 to 18)
    for t in range(0, 19, 2):
        px = viewport.map_x(float(t))
        py_lbl = py_min + 20
        generator.queue_text(px, py_lbl, str(t), font_size=16, color='#000000', align='center')
        
    # 6. Draw Y-axis tick labels (0 to 14)
    for x_val in range(0, 15, 2):
        py = viewport.map_y(float(x_val))
        px_lbl = px_min - 15
        generator.queue_text(px_lbl, py, str(x_val), font_size=16, color='#000000', align='right')
        
    # 7. Draw X and Y axis name labels in dual-styling
    # Y-axis label: x (m) -> x is bold italic, (m) is regular
    generator.queue_text(20, 35, "x", font_size=18, color='#000000', bold=True, italic=True, align='right', width=12, height=30)
    generator.queue_text(26, 35, " (m)", font_size=16, color='#000000', align='left', width=40, height=30)
    
    # X-axis label: t (s) -> t is bold italic, (s) is regular
    generator.queue_text(642, 385, "t", font_size=18, color='#000000', bold=True, italic=True, align='right', width=12, height=30)
    generator.queue_text(648, 385, " (s)", font_size=16, color='#000000', align='left', width=50, height=30)
    
    # 8. Draw three phase markers (double horizontal arrows with labels A, B, C)
    # We place these at y_val = 13 (near top of the grid)
    generator.draw_phase_marker(viewport, x_start=0.0, x_end=5.0, y_val=13.0, label="A", stroke='#0b5394', stroke_width=2.0, font_size=16)
    generator.draw_phase_marker(viewport, x_start=5.0, x_end=12.0, y_val=13.0, label="B", stroke='#38761d', stroke_width=2.0, font_size=16)
    generator.draw_phase_marker(viewport, x_start=12.0, x_end=18.0, y_val=13.0, label="C", stroke='#980000', stroke_width=2.0, font_size=16)
    
    # 9. Draw piecewise curve:
    # Phase A (0,0) -> (5,10)
    px0, py0 = viewport.map_coords(0.0, 0.0)
    px5, py5 = viewport.map_coords(5.0, 10.0)
    generator.queue_line(px0, py0, px5, py5, stroke='#000000', stroke_width=3.5)
    
    # Phase B (5,10) -> (12,10)
    px12, py12 = viewport.map_coords(12.0, 10.0)
    generator.queue_line(px5, py5, px12, py12, stroke='#000000', stroke_width=3.5)
    
    # Phase C (12,10) -> (18,4)
    px18, py18 = viewport.map_coords(18.0, 4.0)
    generator.queue_line(px12, py12, px18, py18, stroke='#000000', stroke_width=3.5)
    
    # 10. Key points markers (at the transition vertices)
    generator.queue_circle(px5, py5, 4.0, stroke='#bf9000', fill='#ffffff', stroke_width=1.5)
    generator.queue_circle(px12, py12, 4.0, stroke='#bf9000', fill='#ffffff', stroke_width=1.5)
    generator.queue_circle(px18, py18, 4.0, stroke='#bf9000', fill='#ffffff', stroke_width=1.5)
    
    # 11. Save local vector outputs
    output_base_path = "test_graph_phases"
    generator.save(f"{output_base_path}.svg")
    
    # 12. Upload structured JSON to Google Slides
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
                name="(x,t)-grafiek met verschillende fases (Widescreen)",
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
