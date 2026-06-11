import ctypes
import json
import os

# ==============================================================================
# WIN32 API CLIPBOARD INTEGRATION
# ==============================================================================
# We use standard Windows 11 ctypes to bind to the User32 and Kernel32 dynamic
# libraries. This permits direct memory-level manipulation of the system pasteboard.
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Defining strict parameter/return types to prevent 64-bit address truncation crashes.
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

# Standard Windows Global Memory allocation flag (0x0002 = GMEM_MOVEABLE)
GMEM_MOVEABLE = 0x0002

# Format registered with Chromium to serialize custom MIME-type key-value data on Windows
CF_CHROMIUM_CUSTOM = user32.RegisterClipboardFormatW("Chromium Web Custom MIME Data Format")
CF_UNICODETEXT = 13  # Standard Windows Unicode Text format ID

def encode_chromium_web_custom(pairs):
    """
    Serializes a list of (mime_type, string_payload) tuples into the binary
    Chromium Web Custom clipboard format buffer.
    
    Format Layout:
    ----------------------------------------------------------------------------
    [4 bytes] Data length of the actual pairs payload
    [4 bytes] Count of pairs (uint32)
    For each pair:
      [4 bytes] Character length of the MIME-type key string
      [N bytes] Key string encoded as UTF-16LE
      [0 or 2 bytes] Null character alignment padding (added if char length is odd)
      [4 bytes] Character length of the serialized JSON value string
      [M bytes] Value string encoded as UTF-16LE
      [0 or 2 bytes] Null character alignment padding (added if char length is odd)
    ----------------------------------------------------------------------------
    """
    data = b""
    for k, v in pairs:
        # Write the key length and character array
        data += len(k).to_bytes(4, "little") + k.encode("utf-16le")
        if len(k) % 2 != 0:
            data += b"\0\0" # Align to 4-byte boundaries if char length is odd
            
        # Write the value length and character array
        data += len(v).to_bytes(4, "little") + v.encode("utf-16le")
        if len(v) % 2 != 0:
            data += b"\0\0" # Align to 4-byte boundaries if char length is odd
            
    # Combine pair count header and pairs data
    total_data = len(pairs).to_bytes(4, "little") + data
    # Prepend the total payload length (excluding this length header itself)
    return len(total_data).to_bytes(4, "little") + total_data

def set_clipboard_data(pairs, text_fallback=""):
    """Writes the compiled custom MIME payload and text fallback to the system clipboard."""
    raw_custom_bytes = encode_chromium_web_custom(pairs)
    if not user32.OpenClipboard(None):
        print("[!] Error: Failed to open clipboard.")
        return False
    try:
        user32.EmptyClipboard()
        
        # Allocate movable global memory for the custom Chromium clipboard payload
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw_custom_bytes))
        if h_mem:
            p_mem = kernel32.GlobalLock(h_mem)
            if p_mem:
                ctypes.memmove(p_mem, raw_custom_bytes, len(raw_custom_bytes))
                kernel32.GlobalUnlock(h_mem)
                user32.SetClipboardData(CF_CHROMIUM_CUSTOM, h_mem)
                print("[+] Successfully wrote Chromium Web Custom MIME Data Format.")
                
        # Allocate movable global memory for fallback standard UnicodeText
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
    print("    WRITING STEP 4: GRID + BORDERS + 31 TEXT LABELS      ")
    print("=========================================================")
    
    # Check if the master backup file exists
    backup_path = os.path.join("clipboard_iterations", "original_graph_structure.json")
    if not os.path.exists(backup_path):
        print(f"[!] Error: Could not find master structure backup: {backup_path}")
        print("    Please run analyze_clipboard.py after copying the original graph.")
        return
        
    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            full_structure = json.load(f)
    except Exception as e:
        print(f"[!] Error loading master JSON structure: {e}")
        return
        
    # Extract the full list of GWT transaction operations
    original_ops = full_structure.get("resolved", [])
    
    # Define our target categories of elements to isolate for Step 4
    border_ids = ["axes_child_18", "axes_child_19", "axes_child_20", "axes_child_21"]
    gridline_ids = [f"axes_child_{i}" for i in range(18)]
    
    # 1. Programmatically identify all Text Box visual elements (shape type 108)
    text_box_ids = set()
    for op in original_ops:
        if isinstance(op, list) and len(op) > 2:
            op_code = op[0]
            obj_id = op[1]
            shape_type = op[2]
            # op_code 3 = Create Shape; shape_type 108 = Text Box
            if op_code == 3 and shape_type == 108:
                text_box_ids.add(obj_id)
                
    print(f"[*] Detected {len(text_box_ids)} text boxes in the original graph.")
    
    # 2. Extract and compile operations belonging only to Borders, Gridlines, or Text Boxes
    step_4_resolved_ops = []
    
    for op in original_ops:
        if not isinstance(op, list) or len(op) < 2:
            continue
            
        op_code = op[0]
        obj_id = op[1]
        
        # Keep border or gridline lines
        if obj_id in border_ids or obj_id in gridline_ids:
            step_4_resolved_ops.append(op)
            
        # Keep text box creations (op_code 3)
        elif op_code == 3 and obj_id in text_box_ids:
            step_4_resolved_ops.append(op)
            
        # Keep text character string insertions (op_code 15)
        elif op_code == 15 and obj_id in text_box_ids:
            step_4_resolved_ops.append(op)
            
        # Keep text formatting / font / paragraph configuration settings (op_code 17)
        elif op_code == 17 and obj_id in text_box_ids:
            step_4_resolved_ops.append(op)
            
    print(f"[*] Compiled {len(step_4_resolved_ops)} total GWT operations for Step 4.")
    
    # 3. Reconstruct 'autotext_content' mappings specifically for active text box shapeIds
    # This prevents Slides from resetting font configurations or discarding blank character maps.
    autotext_content = {}
    for box_id in text_box_ids:
        key_str = json.dumps({"shapeId": box_id})
        autotext_content[key_str] = {}
        
    # Reconstruct inner GWT punch JSON object structure
    inner_payload = {
        "resolved": step_4_resolved_ops,
        "unresolved": step_4_resolved_ops,
        "autotext_content": autotext_content,
        "did_remove_empty_picture_placeholders": False,
        "copy_source_supports_inheritance_via_master": True
    }
    
    flat_data = json.dumps(inner_payload)
    
    # Outer wrapping metadata using official Slide session-specific cryptographic tokens
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
    
    success = set_clipboard_data(pairs, text_fallback="[Google Slides Step 4 Grid + Labels]")
    if success:
        print("\n[+] Step 4 payload (Grid + borders + 31 text labels) placed on system clipboard!")
        print("    Please try pasting (Ctrl+V) directly onto Google Slides.")
    else:
        print("\n[!] Error writing Step 4 payload.")

if __name__ == "__main__":
    main()
