import ctypes
import json
import os

# ==============================================================================
# WIN32 API CLIPBOARD INTEGRATION
# ==============================================================================
# Direct DLL binding using ctypes to access the Windows clipboard handles.
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Function signatures for memory-safe execution on Windows x64.
user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = ctypes.c_bool
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = ctypes.c_bool
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = ctypes.c_bool
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.RegisterClipboardFormatW.argtypes = [ctypes.c_wchar_p]
user32.RegisterClipboardFormatW.restype = ctypes.c_uint

kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_bool

GMEM_MOVEABLE = 0x0002
CF_CHROMIUM_CUSTOM = user32.RegisterClipboardFormatW("Chromium Web Custom MIME Data Format")
CF_UNICODETEXT = 13

def encode_chromium_web_custom(pairs):
    """Serializes key-value MIME pairs into the binary Chromium clipboard format."""
    data = b""
    for k, v in pairs:
        data += len(k).to_bytes(4, "little") + k.encode("utf-16le")
        if len(k) % 2 != 0:
            data += b"\0\0"
        data += len(v).to_bytes(4, "little") + v.encode("utf-16le")
        if len(v) % 2 != 0:
            data += b"\0\0"
    total_data = len(pairs).to_bytes(4, "little") + data
    return len(total_data).to_bytes(4, "little") + total_data

def set_clipboard_data(pairs, text_fallback=""):
    """Writes custom MIME pairs and falling-back standard text to system clipboard."""
    raw_custom_bytes = encode_chromium_web_custom(pairs)
    if not user32.OpenClipboard(None):
        print("[!] Error: Failed to open clipboard.")
        return False
    try:
        user32.EmptyClipboard()
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw_custom_bytes))
        if h_mem:
            p_mem = kernel32.GlobalLock(h_mem)
            if p_mem:
                ctypes.memmove(p_mem, raw_custom_bytes, len(raw_custom_bytes))
                kernel32.GlobalUnlock(h_mem)
                user32.SetClipboardData(CF_CHROMIUM_CUSTOM, h_mem)
                print("[+] Successfully wrote Chromium Web Custom MIME Data Format.")
        if text_fallback:
            text_bytes = (text_fallback + "\0").encode("utf-16le")
            h_text = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_bytes))
            if h_text:
                p_text = kernel32.GlobalLock(h_text)
                if p_text:
                    ctypes.memmove(p_text, text_bytes, len(text_bytes))
                    kernel32.GlobalUnlock(h_text)
                    user32.SetClipboardData(CF_UNICODETEXT, h_text)
                    print("[+] Successfully wrote fallback Unicode Text.")
        return True
    finally:
        user32.CloseClipboard()

def main():
    print("=========================================================")
    print("    WRITING STEP 5: GRID + LABELS + MATH LINES/CURVES    ")
    print("=========================================================")
    
    backup_path = os.path.join("clipboard_iterations", "original_graph_structure.json")
    if not os.path.exists(backup_path):
        print(f"[!] Error: Could not find master structure backup: {backup_path}")
        return
        
    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            full_structure = json.load(f)
    except Exception as e:
        print(f"[!] Error loading master JSON structure: {e}")
        return
        
    original_ops = full_structure.get("resolved", [])
    
    # Target identifiers from previous stages
    border_ids = ["axes_child_18", "axes_child_19", "axes_child_20", "axes_child_21"]
    gridline_ids = [f"axes_child_{i}" for i in range(18)]
    
    # 1. Detect all text boxes (shape type 108)
    text_box_ids = set()
    for op in original_ops:
        if isinstance(op, list) and len(op) > 2:
            op_code = op[0]
            obj_id = op[1]
            shape_type = op[2]
            if op_code == 3 and shape_type == 108:
                text_box_ids.add(obj_id)
                
    # 2. Target Step 5 math lines & curves:
    # - "element_345_line" (Red vertical line)
    # - "element_346_line" (Green vertical line)
    # - "curve_segment_..." (300 small segments making up the black plotted graph curves)
    math_line_ids = ["element_345_line", "element_346_line"]
    
    step_5_resolved_ops = []
    math_lines_count = 0
    curve_segments_count = 0
    
    for op in original_ops:
        if not isinstance(op, list) or len(op) < 2:
            continue
            
        op_code = op[0]
        obj_id = op[1]
        
        # A. Borders and Gridlines (Step 2 & 3)
        if obj_id in border_ids or obj_id in gridline_ids:
            step_5_resolved_ops.append(op)
            
        # B. Text boxes, insertions, and formatting (Step 4)
        elif obj_id in text_box_ids:
            step_5_resolved_ops.append(op)
            
        # C. Math line markers (Step 5)
        elif obj_id in math_line_ids:
            step_5_resolved_ops.append(op)
            math_lines_count += 1
            
        # D. Curve segments making up the plotted graph (Step 5)
        elif obj_id.startswith("curve_segment_"):
            step_5_resolved_ops.append(op)
            curve_segments_count += 1
            
    print(f"[*] Core grid and borders loaded.")
    print(f"[*] Loaded {len(text_box_ids)} text labels.")
    print(f"[*] Added {math_lines_count} custom math lines and {curve_segments_count} curve path segments.")
    print(f"[*] Compiled {len(step_5_resolved_ops)} total GWT operations for Step 5.")
    
    # Build text box character maps in autotext_content
    autotext_content = {}
    for box_id in text_box_ids:
        key_str = json.dumps({"shapeId": box_id})
        autotext_content[key_str] = {}
        
    inner_payload = {
        "resolved": step_5_resolved_ops,
        "unresolved": step_5_resolved_ops,
        "autotext_content": autotext_content,
        "did_remove_empty_picture_placeholders": False,
        "copy_source_supports_inheritance_via_master": True
    }
    
    flat_data = json.dumps(inner_payload)
    
    # Setup GWT transaction envelope
    wrapped_payload = {
        "dih": 1245482604,
        "data": flat_data,
        "edi": "kBeECgZrwyN4Pk3CGalAkiIcibCHBxM0-dGHUMnfHDgyvkMYVZ_pxB9fogazgDhzNcbMktVjXdXLwpNCRHaU0vvKDDCQIvYzhuttxtQqAThS",
        "edrk": "We7cOKI5bHNbFvbICo1cgW8xvwoMCQ_DEW3hRvkC3-q7k9z-tw..",
        "dct": "punch",
        "ds": False,
        "cses": False,
        "sm": "other"
    }
    
    wrapped_str = json.dumps(wrapped_payload)
    
    pairs = [
        ("application/x-vnd.google-docs-drawings-object+wrapped", wrapped_str),
        ("application/x-vnd.google-docs-internal-clip-id", "2519a9aa-7fff-ab00-1255-47f90648ed96")
    ]
    
    success = set_clipboard_data(pairs, text_fallback="[Google Slides Step 5 Grid + Labels + Math Curves]")
    if success:
        print("\n[+] Step 5 payload (Grid + Labels + Math curves) placed on system clipboard!")
        print("    Please try pasting (Ctrl+V) directly onto Google Slides.")
    else:
        print("[!] Error writing Step 5 payload.")

if __name__ == "__main__":
    main()
