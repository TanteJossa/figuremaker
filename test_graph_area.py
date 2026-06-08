import os
import math
import json
from graph_engine import Viewport, AtomicDiagramGenerator
from gslides_uploader import GoogleSlidesUploader, COLORS

def main():
    print("Generating 'Grafiek om oppervlakte onder te bepalen' (Image 4)...")
    
    # 1. Setup Canvas Dimensions (exact widescreen slide 16:9 bounds)
    canvas_w = 720
    canvas_h = 405
    
    # 2. Viewport margins and mathematical limits
    x_min, x_max = 0.0, 12.0
    y_min, y_max = 0.0, 10.0
    
    viewport = Viewport(
        x_min=x_min, x_max=x_max,
        y_min=y_min, y_max=y_max,
        canvas_width=canvas_w, canvas_height=canvas_h,
        margin_left=80, margin_right=40,
        margin_top=50, margin_bottom=50
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
    x_grid_vals = [2.0, 4.0, 6.0, 8.0, 10.0]
    for xv in x_grid_vals:
        px = viewport.map_x(xv)
        generator.queue_line(px, py_max, px, py_min, stroke='#dddddd', stroke_width=1.0, dasharray="4,4")
        
    y_grid_vals = [2.0, 4.0, 6.0, 8.0]
    for yv in y_grid_vals:
        py = viewport.map_y(yv)
        generator.queue_line(px_min, py, px_max, py, stroke='#dddddd', stroke_width=1.0, dasharray="4,4")
        
    # 4. Draw piecewise linear function for v(t)
    def v_func(t):
        if 0.0 <= t < 4.0:
            return 2.0 * t
        elif 4.0 <= t < 8.0:
            return 8.0
        elif 8.0 <= t <= 12.0:
            return 8.0 - 2.0 * (t - 8.0)
        return 0.0

    # 5. Draw the shaded hatched area UNDER the curve
    # Use light blue/grey lines for highly educational look
    generator.draw_hatch_area(
        viewport,
        func_top=v_func,
        func_bottom=lambda t: 0.0,
        x_start=0.0,
        x_end=12.0,
        stroke='#cfe2f3',  # blue_bg
        stroke_width=1.5,
        step_pt=4.0
    )
    
    # 6. Draw solid thick black enclosing boundary frame
    generator.queue_rect(px_min, py_max, plot_w, plot_h, stroke='#000000', stroke_width=3.0, fill='none')
    
    # 7. Draw X-axis tick labels (0 to 12)
    for t in [0, 2, 4, 6, 8, 10, 12]:
        px = viewport.map_x(float(t))
        py_lbl = py_min + 20
        generator.queue_text(px, py_lbl, str(t), font_size=16, color='#000000', align='center')
        
    # 8. Draw Y-axis tick labels (0 to 10)
    for v in [0, 2, 4, 6, 8, 10]:
        py = viewport.map_y(float(v))
        px_lbl = px_min - 15
        generator.queue_text(px_lbl, py, str(v), font_size=16, color='#000000', align='right')
        
    # 9. Draw X and Y axis name labels in dual-styling
    # Y-axis label: v (m/s) -> v is bold italic, (m/s) is regular
    generator.queue_text(20, 35, "v", font_size=18, color='#000000', bold=True, italic=True, align='right', width=12, height=30)
    generator.queue_text(26, 35, " (m/s)", font_size=16, color='#000000', align='left', width=60, height=30)
    
    # X-axis label: t (s) -> t is bold italic, (s) is regular
    generator.queue_text(642, 385, "t", font_size=18, color='#000000', bold=True, italic=True, align='right', width=12, height=30)
    generator.queue_text(648, 385, " (s)", font_size=16, color='#000000', align='left', width=50, height=30)
    
    # 10. Draw key curve segments on top of shaded hatch areas
    # Segment 1: t=0..4, v=0..8
    px0, py0 = viewport.map_coords(0.0, 0.0)
    px4, py4 = viewport.map_coords(4.0, 8.0)
    generator.queue_line(px0, py0, px4, py4, stroke='#000000', stroke_width=3.5)
    
    # Segment 2: t=4..8, v=8
    px8, py8 = viewport.map_coords(8.0, 8.0)
    generator.queue_line(px4, py4, px8, py8, stroke='#000000', stroke_width=3.5)
    
    # Segment 3: t=8..12, v=8..0
    px12, py12 = viewport.map_coords(12.0, 0.0)
    generator.queue_line(px8, py8, px12, py12, stroke='#000000', stroke_width=3.5)
    
    # 11. Draw key markers for the vertices
    generator.queue_circle(px4, py4, 4.0, stroke='#0b5394', fill='#ffffff', stroke_width=1.5)
    generator.queue_circle(px8, py8, 4.0, stroke='#0b5394', fill='#ffffff', stroke_width=1.5)
    
    # Add an educational text centered on the shaded area: "A = ... ?"
    px_area_text = viewport.map_x(6.0)
    py_area_text = viewport.map_y(4.0)
    generator.queue_text(px_area_text, py_area_text, "A = ?", font_size=20, color='#0b5394', bold=True, align='center', mask_bg=True, width=80, height=30)
    
    # 12. Save local vector outputs
    output_base_path = "test_graph_area"
    generator.save(f"{output_base_path}.svg")
    
    # 13. Upload structured JSON to Google Slides
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
                name="Grafiek om oppervlakte onder te bepalen (Widescreen)",
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
