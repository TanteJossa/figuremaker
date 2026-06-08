import xml.etree.ElementTree as ET
import re

def analyze_paths():
    svg_path = "drawings/target_drawing.svg"
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    ns = ""
    m = re.match(r'({[^}]+})', root.tag)
    if m:
        ns = m.group(1)
        
    paths = root.findall(f'.//{ns}path')
    print(f"Total path elements: {len(paths)}")
    
    # Let's group paths by stroke color and fill color
    style_groups = {}
    for i, path in enumerate(paths):
        d = path.attrib.get('d', '')
        style = path.attrib.get('style', '')
        fill = path.attrib.get('fill', 'none')
        stroke = path.attrib.get('stroke', 'none')
        stroke_width = path.attrib.get('stroke-width', 'none')
        stroke_dash = path.attrib.get('stroke-dasharray', 'none')
        
        # Google Drawings SVG styles are often inline in the 'style' attribute or as direct attributes
        style_key = f"fill:{fill} | stroke:{stroke} | stroke-width:{stroke_width} | stroke-dasharray:{stroke_dash} | style:{style}"
        style_groups[style_key] = style_groups.get(style_key, []) + [i]
        
    print("\nPath styling groups:")
    for style_key, indices in sorted(style_groups.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  Group ({len(indices)} paths): {style_key}")
        # Print a sample of d attribute to understand the coordinates
        sample_idx = indices[0]
        sample_path = paths[sample_idx]
        d_val = sample_path.attrib.get('d', '')
        # summarize d_val
        coords = re.findall(r'[MLC]\s*[\d\.-]+\s*[\d\.-]+', d_val)
        print(f"    Sample path {sample_idx} 'd': {d_val[:100]}... (coords count: {len(coords)})")

if __name__ == "__main__":
    analyze_paths()
