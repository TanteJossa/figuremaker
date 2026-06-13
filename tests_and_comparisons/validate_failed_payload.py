import json
import sys

def main():
    print("=== ASSUMPTION VALIDATION LOGS ===")
    try:
        with open("last_clipboard_failed.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading failed clipboard: {e}")
        return

    wrapped = data.get("application/x-vnd.google-docs-drawings-object+wrapped", {})
    if not wrapped:
        print("No wrapped drawing data found.")
        return

    if isinstance(wrapped, str):
        wrapped = json.loads(wrapped)
        
    inner_str = wrapped.get("data", "{}")
    inner = json.loads(inner_str)

    resolved = inner.get("resolved", [])
    unresolved = inner.get("unresolved", [])

    print(f"Total resolved operations: {len(resolved)}")
    print(f"Total unresolved operations: {len(unresolved)}")

    # Let's inspect all unique element IDs and check for duplicates
    # NOTE: Text shapes legitimately have multiple ops (3 create, 15 insert, 17 format)
    #       sharing the same ID. We only flag duplicate SHAPE CREATION IDs as bad.
    element_ids = []
    element_by_id = {}
    shape_creation_duplicates = []
    text_op_reuse_count = 0
    
    # Track op indices
    for idx, op in enumerate(resolved):
        if not isinstance(op, list) or len(op) < 2:
            continue
        op_code = op[0]
        obj_id = op[1]
        element_ids.append(obj_id)
        
        if obj_id in element_by_id:
            # Text ops (15, 17) legitimately reuse the text box shape ID
            if op_code in (15, 17):
                text_op_reuse_count += 1
            else:
                shape_creation_duplicates.append((obj_id, element_by_id[obj_id]["index"], idx, op_code))
        else:
            element_by_id[obj_id] = {"index": idx, "op": op}

    print(f"[*] Text/formatting ops reusing existing shape IDs: {text_op_reuse_count} (expected)")
    if shape_creation_duplicates:
        print(f"[!] Found {len(shape_creation_duplicates)} duplicate SHAPE CREATION IDs:")
        for dup_id, first_idx, second_idx, op_code in shape_creation_duplicates[:20]:
            print(f"  - '{dup_id}' at index {first_idx} and {second_idx} (opcode {op_code})")
    else:
        print("[+] No duplicate SHAPE CREATION IDs found.")

    # Validate Group Operations:
    # 1. Group op must be AFTER all its children in the array
    # 2. All referenced children must exist
    group_ops = []
    for idx, op in enumerate(resolved):
        if not isinstance(op, list) or len(op) < 3:
            continue
        if op[0] == 2: # Group operation
            group_id = op[1]
            children = op[2]
            group_ops.append((idx, group_id, children))

    print(f"\nAnalyzing {len(group_ops)} Group Operations (opcode 2):")
    for idx, group_id, children in group_ops:
        print(f"Group '{group_id}' at resolved index {idx} with {len(children)} children:")
        missing_children = []
        ordered_wrongly = []
        
        for child_id in children:
            if child_id not in element_by_id:
                missing_children.append(child_id)
            else:
                child_idx = element_by_id[child_id]["index"]
                if child_idx >= idx:
                    ordered_wrongly.append((child_id, child_idx))
                    
        if missing_children:
            print(f"  [CRITICAL] Missing children: {missing_children}")
        if ordered_wrongly:
            print(f"  [CRITICAL] Children defined AFTER group (ordered wrongly):")
            for c_id, c_idx in ordered_wrongly:
                print(f"    - '{c_id}' is at index {c_idx} (group is at {idx})")
        if not missing_children and not ordered_wrongly:
            print("  [+] Group structure is valid (all children defined before group).")

    # Let's inspect autotext registrations vs text shapes
    text_shapes = set()
    for op in resolved:
        if len(op) > 2 and op[0] == 3 and op[2] == 108: # TEXT_BOX shape creation
            text_shapes.add(op[1])
            
    registered_autotext = set()
    autotext_content = inner.get("autotext_content", {})
    for k in autotext_content.keys():
        try:
            parsed_k = json.loads(k)
            if "shapeId" in parsed_k:
                registered_autotext.add(parsed_k["shapeId"])
        except Exception as e:
            pass

    unregistered_text = text_shapes - registered_autotext
    if unregistered_text:
        print(f"\n[!] Found {len(unregistered_text)} unregistered text shapes in autotext_content:")
        for shape in list(unregistered_text)[:10]:
            print(f"  - '{shape}'")
    else:
        print("\n[+] All text shapes are registered in autotext_content.")

    # Check for NaN / Infinity
    serialized = json.dumps(inner)
    if "nan" in serialized.lower() or "inf" in serialized.lower():
        print("[!] Found NaN or Inf in serialized JSON!")
    else:
        print("[+] No NaN or Inf found in serialized JSON.")

if __name__ == "__main__":
    main()
