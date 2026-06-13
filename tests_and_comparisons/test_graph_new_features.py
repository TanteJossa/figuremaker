import os
import math
import json
from graph_engine import Viewport, AtomicDiagramGenerator, SVGGroup
from leerlevels_style import COLORS

def main():
    print("Initializing test for new features (boundary_style, axes grouping, axis breaks)...")
    
    canvas_w = 720
    canvas_h = 405
    
    # Range significantly greater than 0 on X and Y to trigger automatic axis break
    x_min, x_max = 50.0, 150.0
    y_min, y_max = 120.0, 220.0
    
    viewport = Viewport(
        x_min=x_min, x_max=x_max,
        y_min=y_min, y_max=y_max,
        canvas_width=canvas_w, canvas_height=canvas_h,
        margin_left=80, margin_right=40,
        margin_top=65, margin_bottom=55
    )
    
    # 1. Test Box-Style with automatic Axis Breaks and Gridlines enabled
    generator_box = AtomicDiagramGenerator(width=canvas_w, height=canvas_h, font_family='Ubuntu')
    
    x_ticks = [60, 80, 100, 120, 140]
    y_ticks = [130, 150, 170, 190, 210]
    
    print("Drawing Box-style graph with breaks and gridlines...")
    generator_box.draw_grid_and_axes(
        viewport, x_ticks, y_ticks,
        x_label="Time (s)", y_label="Temp (K)",
        show_grid=True, show_labels=True,
        boundary_style='box', x_break=True, y_break=True
    )
    
    # Draw a sinusoidal wave function
    def temp_curve(x):
        return 170.0 + 30.0 * math.sin((x - 50.0) * 0.08)
        
    generator_box.draw_math_function(
        viewport, func=temp_curve,
        x_start=50.0, x_end=150.0,
        stroke=COLORS['blue_primary'], stroke_width=3.0,
        group_id="temp_fluctuation_curve"
    )
    
    output_box = "test_new_features_box"
    generator_box.save(f"{output_box}.svg")
    print(f"Saved box-style test to {output_box}.svg / .json")

    # 2. Test Arrow-Style with explicit Axis Breaks and Gridlines disabled
    generator_arrows = AtomicDiagramGenerator(width=canvas_w, height=canvas_h, font_family='Ubuntu')
    
    print("Drawing Arrow-style graph with breaks (gridlines disabled)...")
    generator_arrows.draw_grid_and_axes(
        viewport, x_ticks, y_ticks,
        x_label="Time (s)", y_label="Temp (K)",
        show_grid=False, show_labels=True,
        boundary_style='arrows', x_break=True, y_break=True
    )
    
    generator_arrows.draw_math_function(
        viewport, func=temp_curve,
        x_start=50.0, x_end=150.0,
        stroke=COLORS['green_primary'], stroke_width=3.0,
        group_id="temp_fluctuation_curve_green"
    )
    
    output_arrows = "test_new_features_arrows"
    generator_arrows.save(f"{output_arrows}.svg")
    print(f"Saved arrow-style test to {output_arrows}.svg / .json")
    print("All feature verification tests written successfully!")

if __name__ == "__main__":
    main()
