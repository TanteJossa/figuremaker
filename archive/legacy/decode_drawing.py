import urllib.request
import urllib.error
import re
import os
import xml.etree.ElementTree as ET

def download_drawing_assets():
    drawing_id = "1eSvF7_ekvOWy1q0npqI8f37J9IARPBOZJte5Q3pDspw"
    svg_url = f"https://docs.google.com/drawings/d/{drawing_id}/export/svg"
    png_url = f"https://docs.google.com/drawings/d/{drawing_id}/export/png"
    
    os.makedirs("drawings", exist_ok=True)
    
    svg_path = "drawings/target_drawing.svg"
    png_path = "drawings/target_drawing.png"
    
    print(f"Downloading SVG from: {svg_url}")
    try:
        urllib.request.urlretrieve(svg_url, svg_path)
        print(f"Successfully downloaded SVG to {svg_path}")
    except urllib.error.URLError as e:
        print(f"Error downloading SVG: {e}")
        
    print(f"Downloading PNG from: {png_url}")
    try:
        urllib.request.urlretrieve(png_url, png_path)
        print(f"Successfully downloaded PNG to {png_path}")
    except urllib.error.URLError as e:
        print(f"Error downloading PNG: {e}")

def decode_svg():
    svg_path = "drawings/target_drawing.svg"
    if not os.path.exists(svg_path):
        print(f"Error: {svg_path} does not exist.")
        return
        
    # Analyze raw text for styling
    print("\n=== RAW SVG ANALYTICS ===")
    with open(svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()
        
    print(f"Total characters: {len(svg_content)}")
    
    # Extract unique colors
    # Look for hex colors (e.g., #ffffff, #abc123)
    hex_colors = set(re.findall(r'#[0-9a-fA-F]{6}\b', svg_content))
    print(f"Found unique Hex Colors: {sorted(list(hex_colors))}")
    
    # Look for rgba / rgb colors
    rgb_colors = set(re.findall(r'rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)', svg_content))
    rgba_colors = set(re.findall(r'rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d\.]+\s*\)', svg_content))
    print(f"Found unique RGB Colors: {list(rgb_colors)}")
    print(f"Found unique RGBA Colors: {list(rgba_colors)}")
    
    # Extract font families
    fonts = set(re.findall(r'font-family:\s*[^;"}]+', svg_content))
    print(f"Found unique Font Families: {list(fonts)}")
    
    # Parse XML structure to count shapes
    try:
        # Standard SVG namespace can sometimes block standard element finding if we don't register it
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Remove namespace prefixes for easier parsing
        # Namespace usually looks like {http://www.w3.org/2000/svg}
        ns = ""
        m = re.match(r'({[^}]+})', root.tag)
        if m:
            ns = m.group(1)
            
        print(f"\nviewBox attribute: {root.attrib.get('viewBox')}")
        print(f"width attribute: {root.attrib.get('width')}")
        print(f"height attribute: {root.attrib.get('height')}")
        
        elements_count = {}
        for elem in root.iter():
            tag = elem.tag.replace(ns, "") if ns else elem.tag
            elements_count[tag] = elements_count.get(tag, 0) + 1
            
        print("\nElement counts:")
        for tag, count in elements_count.items():
            print(f"  <{tag}>: {count}")
            
    except Exception as e:
        print(f"XML Parsing error: {e}")

if __name__ == "__main__":
    download_drawing_assets()
    decode_svg()
