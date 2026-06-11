#!/usr/bin/env python3
"""
compare_sine_wave_clipboards.py

Compares the user's current clipboard (last_clipboard.json) against the reference
sine wave structure (clipboard_iterations/test_sine_wave/original_graph_structure.json).

It groups operations by category and compares them, resolving index-shift problems.
"""

import json
import sys
from typing import Any, Dict, List, Set, Tuple

USER_CLIPBOARD_FILE = "last_clipboard.json"
REFERENCE_FILE = "clipboard_iterations/test_sine_wave/original_graph_structure.json"

def get_inner_payload(clipboard_data: Dict) -> Dict:
    wrapped_key = "application/x-vnd.google-docs-drawings-object+wrapped"
    if wrapped_key in clipboard_data:
        wrapped_content = clipboard_data[wrapped_key]
        if isinstance(wrapped_content, dict) and 'data' in wrapped_content:
            try:
                return json.loads(wrapped_content['data'])
            except Exception:
                pass
    if 'resolved' in clipboard_data:
        return clipboard_data
    return {}

def categorize_operations(ops: List[Any]) -> Dict[str, List[Any]]:
    """
    Categorizes the operations into:
    - grid_and_axes: create line ops, or text ops representing axis/grid
    - text_boxes: shape creation, character insertion, formatting
    - curves: mathematical plotted line segments (usually starting with curve_segment)
    - groups: op code 2
    - other: anything else
    """
    categories = {
        "grid_and_axes": [],
        "text_boxes": [],
        "curves": [],
        "groups": [],
        "other": []
    }
    
    # First pass: identify text box IDs and group IDs
    text_box_ids = set()
    group_ids = set()
    
    for op in ops:
        if not isinstance(op, list) or len(op) < 2:
            continue
        op_code = op[0]
        obj_id = op[1]
        
        if op_code == 3 and len(op) > 2 and op[2] == 108: # Shape 108 is Text Box
            text_box_ids.add(obj_id)
        elif op_code == 2:
            group_ids.add(obj_id)
            
    # Second pass: categorize everything
    for op in ops:
        if not isinstance(op, list) or len(op) < 2:
            categories["other"].append(op)
            continue
            
        op_code = op[0]
        obj_id = op[1]
        
        if op_code == 2:
            categories["groups"].append(op)
        elif obj_id in text_box_ids:
            categories["text_boxes"].append(op)
        elif obj_id.startswith("curve_segment_") or obj_id.startswith("cs_"):
            categories["curves"].append(op)
        elif obj_id.startswith("axes_child_") or obj_id.startswith("grid_c_") or "axes" in obj_id or "grid" in obj_id:
            categories["grid_and_axes"].append(op)
        else:
            # Check shape type if create operation
            if op_code == 3 and len(op) > 2:
                shape_type = op[2]
                if shape_type == 153: # line path
                    categories["grid_and_axes"].append(op)
                else:
                    categories["other"].append(op)
            else:
                categories["other"].append(op)
                
    return categories

def clean_and_normalize_op(op: Any, index: int, category: str) -> Any:
    """
    Normalizes object IDs to a clean position-independent placeholder
    so that we can focus on comparing styling and geometries.
    """
    if not isinstance(op, list) or len(op) < 2:
        return op
        
    normalized = list(op)
    # Replace ID
    normalized[1] = f"{category}_element_{index}"
    
    # If it is a group operation (code 2), normalize the children IDs
    if normalized[0] == 2 and len(normalized) > 2 and isinstance(normalized[2], list):
        normalized[2] = [f"{category}_child_{i}" for i in range(len(normalized[2]))]
        
    return normalized

def compare_op_lists(user_ops: List[Any], ref_ops: List[Any], category_name: str) -> List[str]:
    """Compares two lists of operations belonging to the same category."""
    diffs = []
    
    # Sort user and reference ops by some stable metric if possible
    # For shape creation, we can sort by tx/ty coordinates to match them geometrically!
    def get_sort_key(op: Any) -> Tuple[Any, ...]:
        if not isinstance(op, list) or len(op) < 4:
            return (0,)
        op_code = op[0]
        # Sort by op_code first
        # For create shape (code 3), sort by coordinate tx (index 4) and ty (index 5)
        if op_code == 3 and isinstance(op[3], list) and len(op[3]) >= 6:
            return (op_code, op[3][4], op[3][5]) # sort by tx, ty
        # For character insertion (code 15), sort by string value or index
        if op_code == 15 and len(op) >= 5:
            return (op_code, op[4])
        # For formatting (code 17), sort by start and end indices
        if op_code == 17 and len(op) >= 5:
            return (op_code, op[3], op[4])
        return (op_code,)

    try:
        user_sorted = sorted(user_ops, key=get_sort_key)
        ref_sorted = sorted(ref_ops, key=get_sort_key)
    except Exception:
        user_sorted = user_ops
        ref_sorted = ref_ops

    len_u, len_r = len(user_sorted), len(ref_sorted)
    if len_u != len_r:
        diffs.append(f"[{category_name}] Operation count mismatch. User: {len_u}, Reference: {len_r}")
        
    for i in range(min(len_u, len_r)):
        op_u = clean_and_normalize_op(user_sorted[i], i, category_name)
        op_r = clean_and_normalize_op(ref_sorted[i], i, category_name)
        
        if len(op_u) != len(op_r):
            diffs.append(f"[{category_name}][{i}]: Op structure length mismatch. User: {op_u}, Ref: {op_r}")
            continue
            
        for idx in range(len(op_u)):
            val_u, val_r = op_u[idx], op_r[idx]
            if type(val_u) != type(val_r):
                diffs.append(f"[{category_name}][{i}][{idx}]: Type mismatch. User: {type(val_u).__name__} ({val_u}), Ref: {type(val_r).__name__} ({val_r})")
            elif val_u != val_r:
                # If they are floating points, compare with tolerance
                if isinstance(val_u, float) and isinstance(val_r, float):
                    if abs(val_u - val_r) > 0.01:
                        diffs.append(f"[{category_name}][{i}][{idx}]: Value mismatch (Float). User: {val_u:.4f}, Ref: {val_r:.4f}")
                elif isinstance(val_u, list) and isinstance(val_r, list):
                    # Compare list elements
                    if len(val_u) != len(val_r):
                        diffs.append(f"[{category_name}][{i}][{idx}]: List length mismatch. User: {val_u}, Ref: {val_r}")
                    else:
                        for l_idx, (lu, lr) in enumerate(zip(val_u, val_r)):
                            if lu != lr:
                                if isinstance(lu, float) and isinstance(lr, float):
                                    if abs(lu - lr) > 0.01:
                                        diffs.append(f"[{category_name}][{i}][{idx}][{l_idx}]: Float mismatch. User: {lu:.4f}, Ref: {lr:.4f}")
                                else:
                                    diffs.append(f"[{category_name}][{i}][{idx}][{l_idx}]: Value mismatch. User: {lu}, Ref: {lr}")
                else:
                    diffs.append(f"[{category_name}][{i}][{idx}]: Value mismatch. User: {val_u}, Ref: {val_r}")
                    
    return diffs

def main():
    print("--- Categorized Sine Wave Clipboard Comparator ---")
    
    # Load files
    try:
        with open(USER_CLIPBOARD_FILE, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
    except Exception:
        print("[!] Failed to load user clipboard.")
        sys.exit(1)
        
    try:
        with open(REFERENCE_FILE, 'r', encoding='utf-8') as f:
            ref_data = json.load(f)
    except Exception:
        print("[!] Failed to load reference structure.")
        sys.exit(1)
        
    user_payload = get_inner_payload(user_data)
    ref_payload = get_inner_payload(ref_data)
    
    user_resolved = user_payload.get('resolved', [])
    ref_resolved = ref_payload.get('resolved', [])
    
    # Categorize
    u_cats = categorize_operations(user_resolved)
    r_cats = categorize_operations(ref_resolved)
    
    print("\nCategory Operations Count:")
    for cat in ["grid_and_axes", "text_boxes", "curves", "groups", "other"]:
        print(f"  - {cat:<15} | User: {len(u_cats[cat]):<4} | Ref: {len(r_cats[cat]):<4}")
        
    # Compare each category
    all_diffs = []
    for cat in ["grid_and_axes", "text_boxes", "curves", "groups", "other"]:
        diffs = compare_op_lists(u_cats[cat], r_cats[cat], cat)
        all_diffs.extend(diffs)
        
    print("\n--- Differences Found ---")
    if not all_diffs:
        print("[SUCCESS] No structural discrepancies found between User and Reference!")
    else:
        # Group diffs by category for readability
        grouped_diffs = {}
        for diff in all_diffs:
            parts = diff.split("]", 1)
            cat_name = parts[0][1:] if len(parts) > 0 else "unknown"
            if cat_name not in grouped_diffs:
                grouped_diffs[cat_name] = []
            grouped_diffs[cat_name].append(diff)
            
        for cat_name, diff_list in grouped_diffs.items():
            print(f"\n[Category: {cat_name}] ({len(diff_list)} issues):")
            # Only print first 15 of each to avoid spam, but show total count
            for d in diff_list[:15]:
                print(f"  - {d}")
            if len(diff_list) > 15:
                print(f"  ... and {len(diff_list) - 15} more in this category.")

if __name__ == "__main__":
    main()