import os
import subprocess
from formula_pipeline import build_formula_figure

def generate_png(svg_path, png_path):
    print(f"Converting {svg_path} to {png_path} using Inkscape...")
    cmd = [
        r"C:\Program Files\Inkscape\bin\inkscape.COM",
        "--export-filename=" + png_path,
        svg_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Successfully generated {png_path}")

def run_tests():
    # 1. Test Dioptrie
    dioptrie_vars = [
        {"symbol": "S", "color": "blue_primary", "name": "Lenssterkte", "unit": "dpt of m⁻¹", "pos": "left"},
        {"symbol": "f", "color": "yellow_primary", "name": "Brandpuntsafstand", "unit": "m", "pos": "bottom"}
    ]
    print("Generating Dioptrie formula figure...")
    svg_dioptrie = build_formula_figure("{{S}} = \\frac{1}{ {{f}} }", dioptrie_vars, title=None)
    
    os.makedirs("drawings", exist_ok=True)
    svg_path_d = "drawings/test_formula_final.svg"
    png_path_d = "drawings/test_formula_final.png"
    
    with open(svg_path_d, "w", encoding="utf-8") as f:
        f.write(svg_dioptrie)
    generate_png(svg_path_d, png_path_d)
    
    # 2. Test Gauss's Law
    gauss_vars = [
        {"symbol": r"\Phi_E", "color": "green_primary", "name": "Elektrische flux", "unit": "V·m", "pos": "bottom"},
        {"symbol": "E", "color": "red_primary", "name": "Elektrisch veld", "unit": "V/m", "pos": "top"},
        {"symbol": "A", "color": "blue_primary", "name": "Oppervlakte", "unit": "m²", "pos": "bottom"},
        {"symbol": "Q", "color": "yellow_primary", "name": "Omsloten lading", "unit": "C", "pos": "top"},
        {"symbol": r"\varepsilon_0", "color": "blue_primary", "name": "Veldconstante", "unit": "F/m", "pos": "bottom"}
    ]
    
    print("Generating Gauss Law formula figure...")
    svg_gauss = build_formula_figure(
        r"{{\Phi_E}} = \oint {{E}} \cdot d{{A}} = \frac{ {{Q}} }{ {{\varepsilon_0}} }",
        gauss_vars,
        title=None
    )
    
    svg_path_g = "drawings/test_gauss_final.svg"
    png_path_g = "drawings/test_gauss_final.png"
    
    with open(svg_path_g, "w", encoding="utf-8") as f:
        f.write(svg_gauss)
    generate_png(svg_path_g, png_path_g)

if __name__ == "__main__":
    run_tests()
