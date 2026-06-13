#!/usr/bin/env python3
"""
print_ref_texts.py
Parses the reference sine wave original_graph_structure.json and prints out
each text box's ID, text string, and translation/scale coordinates.
"""

import json
import os

REFERENCE_FILE = "clipboard_iterations/test_sine_wave/original_graph_structure.json"

def main():
    if not os.path.exists(REFERENCE_FILE):
        print(f"Error: {REFERENCE_FILE} not found.")
        return

    with open(REFERENCE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    resolved = data.get("resolved", [])
    
    # Map from objectId to text properties
    texts = {}
    for op in resolved:
        if not isinstance(op, list) or len(op) < 2:
            continue
        op_code = op[0]
        obj_id = op[1]
        
        # Op 3: Create shape
        if op_code == 3 and len(op) > 2 and op[2] == 108: # TEXT_BOX
            scale_x, skew_x, skew_y, scale_y, tx, ty = op[3]
            texts[obj_id] = {
                "id": obj_id,
                "scaleX": scale_x,
                "scaleY": scale_y,
                "tx": tx,
                "ty": ty,
                "tx_pt": tx / 508.0,
                "ty_pt": ty / 508.0,
                "width_pt": scale_x * 100000 / 508.0,
                "height_pt": scale_y * 100000 / 508.0,
                "text": ""
            }
        
        # Op 15: Insert characters
        elif op_code == 15 and obj_id in texts:
            texts[obj_id]["text"] = op[4]

    print(f"{'ID':<25} | {'Text':<15} | {'tx (PT)':<10} | {'ty (PT)':<10} | {'width (PT)':<10} | {'height (PT)':<10}")
    print("-" * 90)
    for obj_id, info in sorted(texts.items(), key=lambda x: (x[1]["ty_pt"], x[1]["tx_pt"])):
        print(f"{info['id']:<25} | {info['text']:<15} | {info['tx_pt']:<10.2f} | {info['ty_pt']:<10.2f} | {info['width_pt']:<10.2f} | {info['height_pt']:<10.2f}")

if __name__ == "__main__":
    main()