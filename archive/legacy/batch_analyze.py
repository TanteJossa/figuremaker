import os
import json
import urllib.request
import urllib.error
import re
import xml.etree.ElementTree as ET

def analyze_all_drawings():
    figure_dir = "examples/google-drawing-format/figure"
    if not os.path.exists(figure_dir):
        print(f"Directory {figure_dir} not found.")
        return

    gdraw_files = [f for f in os.listdir(figure_dir) if f.endswith('.gdraw')]
    print(f"Found {len(gdraw_files)} .gdraw files.")

    # Let's take a diverse subset of drawings to analyze
    # Some with Bron, some with Collectie, some with Vraag, etc.
    subset = []
    categories = ["Bron", "Collectie", "Vraag", "Kop"]
    for cat in categories:
        matched = [f for f in gdraw_files if cat in f]
        if matched:
            subset.extend(matched[:3]) # take first 3 of each category
    
    # Fill up to 10 files if needed
    for f in gdraw_files:
        if f not in subset:
            subset.append(f)
        if len(subset) >= 12:
            break

    print(f"Selected {len(subset)} files for detailed programmatic analysis:")
    for f in subset:
        print(f"  - {f}")

    all_hex_colors = set()
    all_fonts = set()
    all_stroke_widths = set()
    all_rx_ry = set()
    
    # Store detail records
    records = []

    os.makedirs("temp_analysis", exist_ok=True)

    for gfile in subset:
        gpath = os.path.join(figure_dir, gfile)
        with open(gpath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"Error parsing {gfile}: {e}")
                continue
            
        doc_id = data.get("doc_id")
        if not doc_id:
            print(f"No doc_id in {gfile}")
            continue

        svg_url = f"https://docs.google.com/drawings/d/{doc_id}/export/svg"
        temp_svg = os.path.join("temp_analysis", f"{doc_id}.svg")

        print(f"\nDownloading and analyzing: {gfile} ({doc_id})")
        try:
            urllib.request.urlretrieve(svg_url, temp_svg)
        except urllib.error.URLError as e:
            print(f"  Error downloading {gfile}: {e}")
            continue

        # Read content
        with open(temp_svg, 'r', encoding='utf-8') as sf:
            content = sf.read()

        # Extract hex colors
        hex_colors = set(re.findall(r'#[0-9a-fA-F]{6}\b', content))
        all_hex_colors.update(hex_colors)

        # Extract fonts
        # Font family in Google SVG is often in inline CSS like font-family:"Ubuntu",sans-serif or font-family:Arial or font-family:"Open Sans"
        fonts = set(re.findall(r'font-family:\s*["\']?([^;"\']+)["\']?', content))
        all_fonts.update(fonts)

        # Parse SVG XML for attributes
        try:
            tree = ET.parse(temp_svg)
            root = tree.getroot()
            ns = ""
            m = re.match(r'({[^}]+})', root.tag)
            if m:
                ns = m.group(1)

            # Check viewbox
            viewbox = root.attrib.get('viewBox', '')
            
            # Find path styles, stroke-widths, rx, ry
            strokes = []
            rx_ry_vals = []
            
            for elem in root.iter():
                # stroke-width
                sw = elem.attrib.get('stroke-width')
                if sw:
                    strokes.append(float(sw))
                    all_stroke_widths.add(float(sw))
                
                # Check style attribute for stroke-width or font-family
                style = elem.attrib.get('style', '')
                if style:
                    sw_match = re.search(r'stroke-width:\s*([\d\.]+)px', style)
                    if sw_match:
                        strokes.append(float(sw_match.group(1)))
                        all_stroke_widths.add(float(sw_match.group(1)))
                    
                    font_match = re.search(r'font-family:\s*["\']?([^;"\']+)["\']?', style)
                    if font_match:
                        all_fonts.add(font_match.group(1))

                # check rx / ry (for roundings)
                rx = elem.attrib.get('rx')
                ry = elem.attrib.get('ry')
                if rx or ry:
                    rx_ry_vals.append((rx, ry))
                    all_rx_ry.add((rx, ry))

            # Sample some elements
            records.append({
                "file": gfile,
                "viewBox": viewbox,
                "colors": sorted(list(hex_colors)),
                "fonts": sorted(list(fonts)),
                "strokes": sorted(list(set(strokes))),
                "roundings": rx_ry_vals[:5]
            })

            print(f"  viewBox: {viewbox}")
            print(f"  Colors: {sorted(list(hex_colors))}")
            print(f"  Fonts: {sorted(list(fonts))}")
            print(f"  Strokes: {sorted(list(set(strokes)))}")
            print(f"  Roundings (rx, ry): {rx_ry_vals}")

        except Exception as xmle:
            print(f"  XML Error: {xmle}")

    print("\n" + "="*50)
    print("GLOBAL ANALYSIS RESULTS:")
    print("="*50)
    print(f"All Unique Hex Colors across subset:\n  {sorted(list(all_hex_colors))}")
    print(f"All Unique Fonts:\n  {sorted(list(all_fonts))}")
    print(f"All Stroke Widths:\n  {sorted(list(all_stroke_widths))}")
    print(f"All Roundings (rx, ry):\n  {sorted(list(all_rx_ry))}")

if __name__ == "__main__":
    analyze_all_drawings()
