import os
import math
import json
from graph_engine import Viewport, AtomicDiagramGenerator
from gslides_uploader import GoogleSlidesUploader, COLORS

def main():
    print("Initializing Atomic Diagram Generator for exact Sinusoidal Graph replica with perfect ordering...")
    
    # 1. Setup Canvas Dimensions (exact widescreen slide 16:9 bounds)
    canvas_w = 720
    canvas_h = 405
    
    # 2. Viewport margins and mathematical limits to fit perfectly
    x_min, x_max = 0.0, 6.0
    y_min, y_max = -0.2, 0.2
    
    viewport = Viewport(
        x_min=x_min, x_max=x_max,
        y_min=y_min, y_max=y_max,
        canvas_width=canvas_w, canvas_height=canvas_h,
        margin_left=80, margin_right=30,
        margin_top=40, margin_bottom=50
    )
    
    # Create the generator with widescreen dimensions and standard font
    generator = AtomicDiagramGenerator(width=canvas_w, height=canvas_h, font_family='Ubuntu')
    
    # Enclosing box coordinates
    px_min = 80
    px_max = 690
    py_min = 355 # bottom edge of grid
    py_max = 40  # top edge of grid
    plot_w = 610
    plot_h = 315
    
    # 3. Draw dashed grid lines (spacing of 0.5 for X, and 0.05 for Y)
    # Vertical grid lines at every 0.5 step
    x_grid_vals = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]
    for xv in x_grid_vals:
        px = viewport.map_x(xv)
        generator.queue_line(px, py_max, px, py_min, stroke='#dddddd', stroke_width=1.0, dasharray="4,4")
        
    # Horizontal grid lines at every 0.05 step
    y_grid_vals = [-0.15, -0.1, -0.05, 0.05, 0.1, 0.15]
    for yv in y_grid_vals:
        py = viewport.map_y(yv)
        generator.queue_line(px_min, py, px_max, py, stroke='#dddddd', stroke_width=1.0, dasharray="4,4")
        
    # 4. Draw horizontal equilibrium line at u = 0.0
    py_zero = viewport.map_y(0.0)
    generator.queue_line(px_min, py_zero, px_max, py_zero, stroke='#999999', stroke_width=1.0)
    
    # 5. Draw solid thick black enclosing boundary frame
    generator.queue_rect(px_min, py_max, plot_w, plot_h, stroke='#000000', stroke_width=3.0, fill='none')
    
    # 6. Draw X-axis tick labels (0 to 6)
    for t in [0, 1, 2, 3, 4, 5, 6]:
        px = viewport.map_x(float(t))
        py_lbl = py_min + 20
        generator.queue_text(px, py_lbl, str(t), font_size=16, color='#000000', align='center')
        
    # 7. Draw Y-axis tick labels with Dutch decimals (using comma!)
    y_ticks_map = [
        (-0.2, "-0,2"),
        (-0.1, "-0,1"),
        (0.0, "0"),
        (0.1, "0,1"),
        (0.2, "0,2")
    ]
    for val, lbl in y_ticks_map:
        py = viewport.map_y(val)
        px_lbl = px_min - 15
        generator.queue_text(px_lbl, py, lbl, font_size=16, color='#000000', align='right')
        
    # 8. Draw X and Y axis name labels in side-by-side boxes for custom dual-styling
    # Y-axis label: u (m) -> u is bold italic, (m) is regular
    generator.queue_text(20, 25, "u", font_size=18, color='#000000', bold=True, italic=True, align='right', width=12, height=30)
    generator.queue_text(26, 25, " (m)", font_size=16, color='#000000', align='left', width=50, height=30)
    
    # X-axis label: t (s) -> t is bold italic, (s) is regular
    generator.queue_text(652, 385, "t", font_size=18, color='#000000', bold=True, italic=True, align='right', width=12, height=30)
    generator.queue_text(658, 385, " (s)", font_size=16, color='#000000', align='left', width=50, height=30)
    
    # 9. Draw Tangent Line 1 (Red passing through Q)
    # Line goes from (2.6, 0.2) to (3.4, -0.2)
    pt1_x, pt1_y = 2.6, 0.2
    pt2_x, pt2_y = 3.4, -0.2
    px1, py1 = viewport.map_coords(pt1_x, pt1_y)
    px2, py2 = viewport.map_coords(pt2_x, pt2_y)
    
    # Red tangent line
    generator.queue_line(px1, py1, px2, py2, stroke='#980000', stroke_width=2.5)
    # Ends circles
    generator.queue_circle(px1, py1, 4.0, stroke='#980000', fill='#ffffff', stroke_width=1.5)
    generator.queue_circle(px2, py2, 4.0, stroke='#980000', fill='#ffffff', stroke_width=1.5)
    
    # Labels with dynamic small white backgrounds to mask overlapping lines
    generator.queue_text(px1, py1 - 22, "(2,6; 0,2)", font_size=16, color='#980000', bold=True, align='center', mask_bg=True, width=95, height=28)
    generator.queue_text(px2 - 12, py2, "(3,4; -0,2)", font_size=16, color='#980000', bold=True, align='right', mask_bg=True, width=115, height=28)
    
    # 10. Draw Tangent Line 2 (Green passing through S)
    # Line goes from (3.6, -0.2) to (4.4, 0.2)
    pt3_x, pt3_y = 3.6, -0.2
    pt4_x, pt4_y = 4.4, 0.2
    px3, py3 = viewport.map_coords(pt3_x, pt3_y)
    px4, py4 = viewport.map_coords(pt4_x, pt4_y)
    
    # Green tangent line
    generator.queue_line(px3, py3, px4, py4, stroke='#38761d', stroke_width=2.5)
    # Ends circles
    generator.queue_circle(px3, py3, 4.0, stroke='#38761d', fill='#ffffff', stroke_width=1.5)
    generator.queue_circle(px4, py4, 4.0, stroke='#38761d', fill='#ffffff', stroke_width=1.5)
    
    # Labels with dynamic small white backgrounds to mask overlapping lines
    generator.queue_text(px4, py4 - 22, "(4,4; 0,2)", font_size=16, color='#38761d', bold=True, align='center', mask_bg=True, width=95, height=28)
    generator.queue_text(px3 + 12, py3, "(3,6; -0,2)", font_size=16, color='#38761d', bold=True, align='left', mask_bg=True, width=115, height=28)
    
    # 11. Main Function Curve: u(t) = 0.16 * sin(pi * t) (solid black, thick, extremely crisp!)
    # Grouped beautifully in SVG under 'sinus_curve' group id
    func_u = lambda t: 0.16 * math.sin(math.pi * t)
    generator.draw_math_function(
        viewport,
        func=func_u,
        x_start=0.0,
        x_end=6.0,
        stroke='#000000',
        stroke_width=3.0,
        steps=300,
        group_id="sinus_curve"
    )
    
    # 12. Draw Key Points (P, Q, R, S) LAST so that they sit perfectly on top of lines
    # Point P (Peak at t=2.5, u=0.16)
    pxP, pyP = viewport.map_coords(2.5, 0.16)
    generator.queue_circle(pxP, pyP, 5.0, stroke='#666666', fill='#ffffff', stroke_width=2.0)
    generator.queue_text(pxP + 12, pyP - 12, "P", font_size=18, color='#666666', bold=True, italic=True, align='left')
    
    # Point R (Valley at t=3.5, u=-0.16)
    pxR, pyR = viewport.map_coords(3.5, -0.16)
    generator.queue_circle(pxR, pyR, 5.0, stroke='#666666', fill='#ffffff', stroke_width=2.0)
    generator.queue_text(pxR + 12, pyR + 12, "R", font_size=18, color='#666666', bold=True, italic=True, align='left')
    
    # Point Q (Crossover at t=3.0, u=0.0)
    pxQ, pyQ = viewport.map_coords(3.0, 0.0)
    generator.queue_circle(pxQ, pyQ, 5.0, stroke='#bf9000', fill='#ffffff', stroke_width=2.0)
    generator.queue_text(pxQ + 12, pyQ - 12, "Q", font_size=18, color='#bf9000', bold=True, italic=True, align='left')
    
    # Point S (Crossover at t=4.0, u=0.0)
    pxS, pyS = viewport.map_coords(4.0, 0.0)
    generator.queue_circle(pxS, pyS, 5.0, stroke='#bf9000', fill='#ffffff', stroke_width=2.0)
    generator.queue_text(pxS + 12, pyS - 12, "S", font_size=18, color='#bf9000', bold=True, italic=True, align='left')
    
    # 13. Save local vector outputs
    output_base_path = "test_sinus_graph"
    generator.save(f"{output_base_path}.svg")
    
    # 14. Upload structured JSON to Google Slides
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
                name="Exact replica of Wavelength Sinusoid with tangents (Ubuntu Font)",
                folder_id=os.environ.get("DRIVE_FOLDER_ID")
            )
            print("\n" + "="*80)
            print("NATIVE GOOGLE SLIDES DIAGRAM CREATED SUCCESSFULLY!")
            print(f"Presentation Link: {presentation_file.get('webViewLink')}")
            print("="*80 + "\n")
        except Exception as e:
            print(f"\nFailed to upload diagram to Google Slides: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"Error: Could not find serialized JSON file: {json_path}")


if __name__ == "__main__":
    main()
