import os
import math
import json
from graph_engine import Viewport, AtomicDiagramGenerator, SVGGroup
from leerlevels_style import draw_line
from gslides_uploader import GoogleSlidesUploader, COLORS

def lorenz_system(x, y, z, s=10.0, r=28.0, b=8.0/3.0):
    dx = s * (y - x)
    dy = x * (r - z) - y
    dz = x * y - b * z
    return dx, dy, dz

def main():
    print("Initializing Atomic Diagram Generator for Lorenz Attractor with LaTeX labels...")
    
    # 1. Setup Canvas Dimensions (exact widescreen slide 16:9 bounds)
    canvas_w = 720
    canvas_h = 405
    
    # 2. Viewport margins and mathematical limits
    # Lorenz attractor projections on X-Z plane typically lie in:
    # X in [-20, 20], Z in [0, 50].
    # Let's set our math boundaries with comfortable padding.
    x_min, x_max = -25.0, 25.0
    y_min, y_max = -5.0, 55.0
    
    viewport = Viewport(
        x_min=x_min, x_max=x_max,
        y_min=y_min, y_max=y_max,
        canvas_width=canvas_w, canvas_height=canvas_h,
        margin_left=80, margin_right=40,
        margin_top=65, margin_bottom=55
    )
    
    # Create the generator with widescreen dimensions and standard font
    generator = AtomicDiagramGenerator(width=canvas_w, height=canvas_h, font_family='Ubuntu')
    
    # Grid dimensions in presentation points (PT)
    px_min = 80
    px_max = 680
    py_min = 350 # bottom edge of grid
    py_max = 65  # top edge of grid
    plot_w = 600
    plot_h = 285
    
    # 3. Draw dashed grid lines (spacing of 10 for X, and 10 for Y)
    x_grid_vals = [-20.0, -10.0, 0.0, 10.0, 20.0]
    for xv in x_grid_vals:
        px = viewport.map_x(xv)
        generator.queue_line(px, py_max, px, py_min, stroke='#dddddd', stroke_width=1.0, dasharray="4,4")
        
    y_grid_vals = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0]
    for yv in y_grid_vals:
        py = viewport.map_y(yv)
        generator.queue_line(px_min, py, px_max, py, stroke='#dddddd', stroke_width=1.0, dasharray="4,4")
        
    # 4. Generate Lorenz Attractor high-density trajectory
    s, r, b = 10.0, 28.0, 8.0/3.0
    dt = 0.015
    num_steps = 1000
    
    x, y, z = 0.1, 0.0, 0.0
    points = []
    for _ in range(num_steps):
        dx, dy, dz = lorenz_system(x, y, z, s, r, b)
        x += dx * dt
        y += dy * dt
        z += dz * dt
        # Projecting onto the X-Z plane
        points.append((x, z))
        
    # 5. Create line segments for the high-density parametric curve
    curve_segments = []
    for i in range(len(points) - 1):
        pt1 = points[i]
        pt2 = points[i+1]
        
        # Clip coordinates within math range to avoid rendering artifacts outside frame
        if x_min <= pt1[0] <= x_max and y_min <= pt1[1] <= y_max:
            if x_min <= pt2[0] <= x_max and y_min <= pt2[1] <= y_max:
                px1, py1 = viewport.map_coords(pt1[0], pt1[1])
                px2, py2 = viewport.map_coords(pt2[0], pt2[1])
                
                # Draw the trajectory line segment
                curve_segments.append(
                    draw_line(px1, py1, px2, py2, stroke=COLORS['blue_primary'], stroke_width=1.8)
                )
                
    # Wrap all curve segments in an SVGGroup so they stay grouped in Google Slides
    if curve_segments:
        generator.add(SVGGroup("lorenz_attractor_trajectory", curve_segments))
        print(f"Added Lorenz attractor trajectory with {len(curve_segments)} segments.")
        
    # 6. Draw solid thick black enclosing boundary frame
    generator.queue_rect(px_min, py_max, plot_w, plot_h, stroke='#000000', stroke_width=3.0, fill='none')
    
    # 7. Draw X-axis tick labels
    for tx in [-20, -10, 0, 10, 20]:
        px = viewport.map_x(float(tx))
        py_lbl = py_min + 20
        generator.queue_text(px, py_lbl, str(tx), font_size=15, color='#000000', align='center')
        
    # 8. Draw Y-axis tick labels
    for ty in [0, 10, 20, 30, 40, 50]:
        py = viewport.map_y(float(ty))
        px_lbl = px_min - 15
        generator.queue_text(px_lbl, py, str(ty), font_size=15, color='#000000', align='right')
        
    # 9. Draw LaTeX math title/labels
    # Main system equation label centered above the plot
    generator.draw_latex(
        r"\frac{dx}{dt}=\sigma(y-x), \ \frac{dy}{dt}=x(\rho-z)-y, \ \frac{dz}{dt}=xy-\beta z",
        x=360, y=20, font_size=20, color=COLORS['black'], align='center', group_id='latex_eq_system'
    )
    
    # Parameter values centered just below main equation
    generator.draw_latex(
        r"\sigma = 10, \ \rho = 28, \ \beta = \frac{8}{3}",
        x=360, y=44, font_size=16, color=COLORS['dark_gray'], align='center', group_id='latex_eq_params'
    )
    
    # Initial state condition label placed inside plot area (bottom center)
    generator.draw_latex(
        r"\mathbf{x}_0 = (0.1, \ 0, \ 0)",
        x=360, y=328, font_size=15, color=COLORS['red_primary'], align='center', group_id='latex_init_state'
    )
    
    # Left lobe center (equilibrium point C1) label inside plot
    generator.draw_latex(
        r"C_1 = (-\sqrt{\beta(\rho-1)}, \ -\sqrt{\beta(\rho-1)}, \ \rho-1)",
        x=185, y=140, font_size=13, color=COLORS['green_primary'], align='center', group_id='latex_c1_eq'
    )
    
    # Right lobe center (equilibrium point C2) label inside plot
    generator.draw_latex(
        r"C_2 = (\sqrt{\beta(\rho-1)}, \ \sqrt{\beta(\rho-1)}, \ \rho-1)",
        x=535, y=140, font_size=13, color=COLORS['green_primary'], align='center', group_id='latex_c2_eq'
    )
    
    # 10. Draw LaTeX Axis labels
    # X-axis label: x(t)
    generator.draw_latex(
        r"x(t)",
        x=695, y=viewport.map_y(0.0), font_size=16, color=COLORS['black'], align='left', group_id='latex_axis_x'
    )
    
    # Y-axis label: z(t)
    generator.draw_latex(
        r"z(t)",
        x=80, y=35, font_size=16, color=COLORS['black'], align='center', group_id='latex_axis_y'
    )
    
    # 11. Save local vector outputs
    output_base_path = "test_graph_diffeq"
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
                name="Complex Differential Equation (Lorenz Attractor) & LaTeX Labels",
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
