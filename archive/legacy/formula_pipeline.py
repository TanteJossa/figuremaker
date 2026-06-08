import os
import re
import subprocess
import tempfile
import logging
import xml.etree.ElementTree as ET
from leerlevels_style import Canvas, COLORS, draw_rect, draw_text, draw_line

logger = logging.getLogger("figuremaker.formula")

# Map of standard color names to hex codes
COLOR_MAP = {
    'red_primary': '#980000',
    'blue_primary': '#0b5394',
    'green_primary': '#38761d',
    'yellow_primary': '#bf9000',
    'purple_primary': '#674ea7',
    'black': '#000000'
}

def clean_unit(unit_str):
    if not unit_str:
        return ""
    # Replace LaTeX \cdot to center dot ·
    unit_str = unit_str.replace(r"\cdot", "·").replace(r" \cdot ", "·").replace(r" \cdot", "·").replace(r"\cdot ", "·")
    # Replace LaTeX superscripts to native unicode superscript characters
    unit_str = unit_str.replace("^{-1}", "⁻¹").replace("^-1", "⁻¹")
    unit_str = unit_str.replace("^{2}", "²").replace("^2", "²")
    unit_str = unit_str.replace("^{3}", "³").replace("^3", "³")
    # Clean up braces and carats
    unit_str = unit_str.replace("{", "").replace("}", "").replace("^", "")
    return unit_str

# Mapping hex colors back to variable identifiers to locate them in the SVG
def hex_to_rgb_normalized(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = "".join([c*2 for c in hex_str])
    r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
    return r, g, b

def get_path_bbox(d_string):
    """
    Parses absolute/relative commands in an SVG path d-string and returns (xmin, ymin, xmax, ymax)
    """
    tokens = re.findall(r'([A-Za-z]|-?\d*\.\d+|-?\d+)', d_string)
    
    xs = []
    ys = []
    
    curr_x = 0.0
    curr_y = 0.0
    
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.isalpha():
            cmd = token
            i += 1
            if cmd in ('M', 'L', 'T'):
                if i + 1 < len(tokens):
                    curr_x = float(tokens[i])
                    curr_y = float(tokens[i+1])
                    xs.append(curr_x)
                    ys.append(curr_y)
                    i += 2
            elif cmd == 'H':
                if i < len(tokens):
                    curr_x = float(tokens[i])
                    xs.append(curr_x)
                    ys.append(curr_y)
                    i += 1
            elif cmd == 'V':
                if i < len(tokens):
                    curr_y = float(tokens[i])
                    xs.append(curr_x)
                    ys.append(curr_y)
                    i += 1
            elif cmd == 'C':
                if i + 5 < len(tokens):
                    curr_x = float(tokens[i+4])
                    curr_y = float(tokens[i+5])
                    xs.extend([float(tokens[i]), float(tokens[i+2]), curr_x])
                    ys.extend([float(tokens[i+1]), float(tokens[i+3]), curr_y])
                    i += 6
            elif cmd in ('S', 'Q'):
                if i + 3 < len(tokens):
                    curr_x = float(tokens[i+2])
                    curr_y = float(tokens[i+3])
                    xs.extend([float(tokens[i]), curr_x])
                    ys.extend([float(tokens[i+1]), curr_y])
                    i += 4
            elif cmd == 'A':
                if i + 6 < len(tokens):
                    curr_x = float(tokens[i+5])
                    curr_y = float(tokens[i+6])
                    xs.append(curr_x)
                    ys.append(curr_y)
                    i += 7
            elif cmd in ('Z', 'z'):
                pass
            # Lowercase commands (relative)
            elif cmd in ('m', 'l', 't'):
                if i + 1 < len(tokens):
                    curr_x += float(tokens[i])
                    curr_y += float(tokens[i+1])
                    xs.append(curr_x)
                    ys.append(curr_y)
                    i += 2
            elif cmd == 'h':
                if i < len(tokens):
                    curr_x += float(tokens[i])
                    xs.append(curr_x)
                    ys.append(curr_y)
                    i += 1
            elif cmd == 'v':
                if i < len(tokens):
                    curr_y += float(tokens[i])
                    xs.append(curr_x)
                    ys.append(curr_y)
                    i += 1
            elif cmd == 'c':
                if i + 5 < len(tokens):
                    x1 = curr_x + float(tokens[i])
                    y1 = curr_y + float(tokens[i+1])
                    x2 = curr_x + float(tokens[i+2])
                    y2 = curr_y + float(tokens[i+3])
                    curr_x += float(tokens[i+4])
                    curr_y += float(tokens[i+5])
                    xs.extend([x1, x2, curr_x])
                    ys.extend([y1, y2, curr_y])
                    i += 6
            elif cmd in ('s', 'q'):
                if i + 3 < len(tokens):
                    x1 = curr_x + float(tokens[i])
                    y1 = curr_y + float(tokens[i+1])
                    curr_x += float(tokens[i+2])
                    curr_y += float(tokens[i+3])
                    xs.extend([x1, curr_x])
                    ys.extend([y1, curr_y])
                    i += 4
            elif cmd == 'a':
                if i + 6 < len(tokens):
                    curr_x += float(tokens[i+5])
                    curr_y += float(tokens[i+6])
                    xs.append(curr_x)
                    ys.append(curr_y)
                    i += 7
        else:
            try:
                val = float(token)
                xs.append(val)
                i += 1
            except ValueError:
                i += 1
                
    if not xs or not ys:
        return 0, 0, 0, 0
    return min(xs), min(ys), max(xs), max(ys)

def compile_latex_to_svg(latex_math, extra_preamble=""):
    """
    Compiles standard LaTeX formula to SVG string.
    """
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
""" % (extra_preamble, latex_math)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "formula.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_template)
            
        try:
            cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "formula.tex"]
            subprocess.run(cmd, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"pdflatex compilation failed: {e.stdout}")
            raise Exception(f"LaTeX compilation failed: {e.stdout}")
            
        pdf_path = os.path.join(tmpdir, "formula.pdf")
        svg_path = os.path.join(tmpdir, "formula.svg")
        
        try:
            cmd_svg = ["dvisvgm", "--pdf", "--no-fonts", "formula.pdf", "-o", "formula.svg"]
            subprocess.run(cmd_svg, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"dvisvgm conversion failed: {e.stdout}")
            raise Exception(f"dvisvgm conversion failed: {e.stdout}")
            
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
            
        return svg_content

def hex_matches(color1, color2):
    """
    Normalizes hex strings to check for equivalence (e.g., #f00 == #ff0000)
    """
    c1 = color1.lower().lstrip('#')
    c2 = color2.lower().lstrip('#')
    if len(c1) == 3:
        c1 = "".join([x*2 for x in c1])
    if len(c2) == 3:
        c2 = "".join([x*2 for x in c2])
    return c1 == c2

def build_formula_figure(latex_template, variables, title=None, font_family='Ubuntu'):
    r"""
    Assembles a complete, spec-compliant Leerlevels styled formula diagram.
    - latex_template: e.g. "{{M}} \quad = \quad {{F}} \quad \cdot \quad {{d}}"
    - variables: list of dicts, e.g. [
          {"symbol": "M", "color": "green_primary", "name": "Koppelmoment", "unit": "N\\cdot m", "pos": "bottom"},
          ...
      ]
    - title: Can be a centered title string OR a list of styled parts for rich semantic text coloring:
      e.g., [{"text": "De "}, {"text": "sterkte", "color": "blue_primary", "bold": True}, ...]
    """
    # 1. Substitute variables in latex_template with colored commands
    latex_math = latex_template
    preamble_parts = []
    
    # Define LaTeX colors
    for name, hex_code in COLOR_MAP.items():
        preamble_parts.append(f"\\definecolor{{{name}}}{{HTML}}{{{hex_code.lstrip('#').upper()}}}")
        
    extra_preamble = "\n".join(preamble_parts)
    
    # Perform placeholders substitution
    # If the template uses {{var}}, replace it. If not, fallback to literal replacements.
    for var in variables:
        sym = var["symbol"]
        color_name = var["color"]
        # Replace {{sym}} with \textcolor{color_name}{sym}
        latex_math = latex_math.replace(f"{{{{{sym}}}}}", f"\\textcolor{{{color_name}}}{{{sym}}}")
        
    logger.info(f"Substituted LaTeX: {latex_math}")
    
    # 2. Render LaTeX formula to pure path SVG
    formula_svg = compile_latex_to_svg(latex_math, extra_preamble)
    
    # Parse the generated SVG
    tree = ET.ElementTree(ET.fromstring(formula_svg))
    root = tree.getroot()
    
    # Strip namespaces to solve the invisible formula issue
    def strip_namespaces(el):
        if el.tag.startswith('{'):
            el.tag = el.tag.split('}', 1)[1]
        for key in list(el.attrib.keys()):
            if key.startswith('{'):
                new_key = key.split('}', 1)[1]
                if "xlink" in key or "1999/xlink" in key:
                    new_key = "xlink:" + new_key
                el.attrib[new_key] = el.attrib.pop(key)
        for child in el:
            strip_namespaces(child)
            
    strip_namespaces(root)
    
    # Read viewBox of formula SVG to get native size
    viewbox = root.attrib.get("viewBox", "0 0 100 20")
    parts = [float(x) for x in viewbox.split()]
    v_xmin, v_ymin, v_w, v_h = parts[0], parts[1], parts[2], parts[3]
    
    # 3. Find bounding box of each colored variable
    var_bboxes = {} # maps color hex -> list of coordinates
    
    # Traverse paths to extract bounding boxes
    for elem in root.iter():
        tag = elem.tag.split('}')[-1]
        if tag == 'path':
            fill = elem.attrib.get('fill', '#000000')
            d = elem.attrib.get('d', '')
            if d:
                xmin, ymin, xmax, ymax = get_path_bbox(d)
                if xmin == 0 and xmax == 0:
                    continue
                # Add to appropriate color bucket
                found_color = None
                for name, hex_code in COLOR_MAP.items():
                    if hex_matches(fill, hex_code):
                        found_color = name
                        break
                if found_color and found_color != 'black':
                    if found_color not in var_bboxes:
                        var_bboxes[found_color] = []
                    var_bboxes[found_color].append((xmin, ymin, xmax, ymax))
                    
    # Group bboxes of the same color into separate variables left-to-right, accounting for vertical matrix flip
    color_variable_instances = {}
    for color_name, bboxes in var_bboxes.items():
        # Sort bboxes by center X
        bboxes.sort(key=lambda b: (b[0] + b[2]) / 2.0)
        
        # Group bboxes that are close horizontally (threshold of 40.0 local points)
        groups = []
        for b in bboxes:
            if not groups:
                groups.append([b])
            else:
                last_group = groups[-1]
                lg_xmax = max(item[2] for item in last_group)
                if b[0] - lg_xmax < 40.0:
                    last_group.append(b)
                else:
                    groups.append([b])
                    
        # Compute centers and ranges for each group
        instances = []
        for group in groups:
            xmins = [g[0] for g in group]
            ymins = [g[1] for g in group]
            xmaxs = [g[2] for g in group]
            ymaxs = [g[3] for g in group]
            
            overall_xmin = min(xmins)
            overall_ymin = min(ymins)
            overall_xmax = max(xmaxs)
            overall_ymax = max(ymaxs)
            
            cx = (overall_xmin + overall_xmax) / 2.0
            cy = (overall_ymin + overall_ymax) / 2.0
            
            instances.append({
                "center": (cx, cy),
                "range": (overall_xmin, overall_ymin, overall_xmax, overall_ymax)
            })
            
        color_variable_instances[color_name] = instances
        logger.info(f"Color '{color_name}' has {len(instances)} distinct spatial variable instances.")

    # 4. Construct final canvas composition
    canvas = Canvas(font_family=font_family)
    
    # Centered placement parameters for formula (perfectly centered on the 562.5 canvas)
    target_cx = 500.0
    target_cy = 281.25
    
    # Calculate scale so formula height is ~130px (much larger and bolder)
    target_fh = 130.0
    scale = target_fh / v_h
    
    # Cap the scale so the formula doesn't exceed 850px width
    if v_w * scale > 850.0:
        scale = 850.0 / v_w
        target_fh = v_h * scale
        
    local_f_cx = v_xmin + v_w / 2.0
    # Center of local dvisvgm formula is at v_ymin + v_h / 2.0.
    # Due to matrix(1 0 0 -1 0 0) flipping, Y_screen = ty - y_local * scale.
    # To place this center at target_cy, target_cy = ty - (v_ymin + v_h / 2.0) * scale.
    # So, ty = target_cy - (v_ymin + v_h / 2.0) * scale.
    tx = target_cx - local_f_cx * scale
    ty = target_cy - (v_ymin + v_h / 2.0) * scale
    
    # Extract original child elements of dvisvgm <svg> tag as raw XML strings to preserve matrix transforms
    svg_children = []
    for child in root:
        child_str = ET.tostring(child, encoding='utf-8').decode('utf-8')
        svg_children.append(child_str)
        
    group_xml = f'<g transform="translate({tx:.3f}, {ty:.3f}) scale({scale:.4f})">\n' + "\n".join(svg_children) + '\n</g>'
    canvas.add(group_xml)
    
    # 5. Place annotations (NO connecting guide lines!)
    color_usage_counters = {} # maps color_name -> index of current instance
    
    for var in variables:
        color_name = var["color"]
        symbol = var["symbol"]
        name = var["name"]
        unit = clean_unit(var.get("unit", ""))
        pos = var.get("pos", "bottom") # "left", "right", "bottom", "top"
        
        # Determine canvas absolute coordinates using multi-instance counter
        instances = color_variable_instances.get(color_name, [])
        idx = color_usage_counters.get(color_name, 0)
        
        if idx < len(instances):
            inst = instances[idx]
            color_usage_counters[color_name] = idx + 1
            
            local_cx, local_cy = inst["center"]
            local_xmin, local_ymin, local_xmax, local_ymax = inst["range"]
            
            canvas_x = tx + local_cx * scale
            canvas_y = ty - local_cy * scale
            canvas_xmin = tx + local_xmin * scale
            canvas_xmax = tx + local_xmax * scale
            canvas_ymin = ty - local_ymax * scale
            canvas_ymax = ty - local_ymin * scale
        else:
            # Fallback
            canvas_x = target_cx
            canvas_y = target_cy
            canvas_xmin = target_cx - 20
            canvas_xmax = target_cx + 20
            canvas_ymin = target_cy - 20
            canvas_ymax = target_cy + 20
            
        color_hex = COLOR_MAP.get(color_name, COLOR_MAP['black'])
        
        # Calculate label positioning coordinates according to Formula-Only Style Guide
        # Symmetrical fixed baseline system for perfect, clean vertical alignment
        if pos == "bottom":
            label_x = canvas_x
            align = "center"
            name_y = 410.0
            unit_y = 432.0
        elif pos == "top":
            label_x = canvas_x
            align = "center"
            name_y = 135.0
            unit_y = 157.0
        elif pos == "left":
            label_x = canvas_xmin - 35.0
            align = "right"
            name_y = 270.25
            unit_y = 292.25
        elif pos == "right":
            label_x = canvas_xmax + 35.0
            align = "left"
            name_y = 270.25
            unit_y = 292.25
        else:
            # Default fallback to bottom
            label_x = canvas_x
            align = "center"
            name_y = 410.0
            unit_y = 432.0
            
        # Draw Name: regular weight, NOT bold
        canvas.add(draw_text(
            x=label_x, 
            y=name_y, 
            text=name, 
            font_size=18, 
            color=color_hex, 
            bold=False, 
            align=align
        ))
        
        # Draw Unit: BOLD
        if unit:
            unit_text = f"({unit})"
            canvas.add(draw_text(
                x=label_x, 
                y=unit_y, 
                text=unit_text, 
                font_size=15, 
                color=color_hex, 
                bold=True, 
                align=align
            ))
            
    return canvas.render()

if __name__ == "__main__":
    # Test compilation (Dioptrie formula)
    test_variables = [
        {"symbol": "S", "color": "blue_primary", "name": "Lenssterkte", "unit": "dpt of m⁻¹", "pos": "left"},
        {"symbol": "f", "color": "yellow_primary", "name": "Brandpuntsafstand", "unit": "m", "pos": "bottom"}
    ]
    svg = build_formula_figure("{{S}} = \\frac{1}{ {{f}} }", test_variables, title=None)
    with open("test_formula_final.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("Test formula SVG written successfully to 'test_formula_final.svg'.")
