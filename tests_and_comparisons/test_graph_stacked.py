import os
import math
import json
from graph_engine import Viewport, AtomicDiagramGenerator
from gslides_uploader import GoogleSlidesUploader, COLORS

def main():
    print("Generating 'Stacked Area Chart with Legend' (Image 6)...")
    
    # 1. Setup Canvas Dimensions (exact widescreen slide 16:9 bounds)
    canvas_w = 720
    canvas_h = 405
    
    # 2. Viewport margins and mathematical limits
    x_min, x_max = 0.0, 10.0
    y_min, y_max = 0.0, 6.0
    
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
    
    # 3. Draw dashed grid lines (spacing of 1 for X, and 1 for Y)
    x_grid_vals = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    for xv in x_grid_vals:
        px = viewport.map_x(xv)
        generator.queue_line(px, py_max, px, py_min, stroke='#dddddd', stroke_width=1.0, dasharray="4,4")
        
    y_grid_vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    for yv in y_grid_vals:
        py = viewport.map_y(yv)
        generator.queue_line(px_min, py, px_max, py, stroke='#dddddd', stroke_width=1.0, dasharray="4,4")
        
    # 4. Define Stacked curves mathematically
    # Bottom layer: Renewables (grows over time)
    f1 = lambda t: 1.0 + 0.15 * t
    
    # Middle layer: Gas (placed on top of f1)
    f2 = lambda t: f1(t) + (1.5 - 0.05 * t)
    
    # Top layer: Coal (placed on top of f2)
    f3 = lambda t: f2(t) + (2.0 - 0.15 * t)
    
    # 5. Draw the shaded hatched areas for each layer
    # Layer 1: Renewables (Green)
    generator.draw_hatch_area(
        viewport,
        func_top=f1,
        func_bottom=lambda t: 0.0,
        x_start=0.0,
        x_end=10.0,
        stroke='#38761d',  # green_primary
        stroke_width=1.0,
        step_pt=4.0
    )
    
    # Layer 2: Gas (Blue)
    generator.draw_hatch_area(
        viewport,
        func_top=f2,
        func_bottom=f1,
        x_start=0.0,
        x_end=10.0,
        stroke='#0b5394',  # blue_primary
        stroke_width=1.0,
        step_pt=4.0
    )
    
    # Layer 3: Coal (Red)
    generator.draw_hatch_area(
        viewport,
        func_top=f3,
        func_bottom=f2,
        x_start=0.0,
        x_end=10.0,
        stroke='#980000',  # red_primary
        stroke_width=1.0,
        step_pt=4.0
    )
    
    # 6. Draw solid thick black enclosing boundary frame
    generator.queue_rect(px_min, py_max, plot_w, plot_h, stroke='#000000', stroke_width=3.0, fill='none')
    
    # 7. Draw X-axis tick labels (0 to 10)
    for t in range(0, 11):
        px = viewport.map_x(float(t))
        py_lbl = py_min + 20
        generator.queue_text(px, py_lbl, str(t), font_size=16, color='#000000', align='center')
        
    # 8. Draw Y-axis tick labels (0 to 6)
    for y_val in range(0, 7):
        py = viewport.map_y(float(y_val))
        px_lbl = px_min - 15
        generator.queue_text(px_lbl, py, str(y_val), font_size=16, color='#000000', align='right')
        
    # 9. Draw X and Y axis name labels in dual-styling
    # Y-axis label: E (GJ) -> E is bold italic, (GJ) is regular
    generator.queue_text(20, 35, "E", font_size=18, color='#000000', bold=True, italic=True, align='right', width=12, height=30)
    generator.queue_text(26, 35, " (GJ)", font_size=16, color='#000000', align='left', width=50, height=30)
    
    # X-axis label: t (jaar) -> t is bold italic, (jaar) is regular
    generator.queue_text(642, 385, "t", font_size=18, color='#000000', bold=True, italic=True, align='right', width=12, height=30)
    generator.queue_text(648, 385, " (jaar)", font_size=16, color='#000000', align='left', width=60, height=30)
    
    # 10. Draw solid crisp curve lines on top of the shaded hatch areas
    generator.draw_math_function(viewport, func=f1, stroke='#274e13', stroke_width=2.5, group_id="renewables_border")
    generator.draw_math_function(viewport, func=f2, stroke='#073763', stroke_width=2.5, group_id="gas_border")
    generator.draw_math_function(viewport, func=f3, stroke='#660000', stroke_width=2.5, group_id="coal_border")
    
    # 11. Draw a beautiful custom Legend Box in the top-right corner of the plot area
    # Box position: x = 500, y = 65
    generator.draw_legend(
        x=510, y=65,
        items=[
            ("Kolen (Coal)", "#980000"),
            ("Gas (Gas)", "#0b5394"),
            ("Hernieuwbaar", "#38761d")
        ],
        width=150,
        font_size=12
    )
    
    # 12. Save local vector outputs
    output_base_path = "test_graph_stacked"
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
                name="Gestapelde Grafiek met Legenda (Widescreen)",
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
