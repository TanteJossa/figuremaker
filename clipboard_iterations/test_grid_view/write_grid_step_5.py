import ctypes
import json
import os

# Win32 clipboard constants and functions
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

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
    """Encodes custom MIME type pairs into Chromium's custom format buffer structure."""
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
    """Writes custom MIME pairs and a fallback plain text string to the Windows clipboard."""
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
            else:
                print("[!] Error: Failed to lock memory.")
        else:
            print("[!] Error: Failed to allocate memory.")
                
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
    print("   WRITING GRID STEP 5: STEP 4 + GREEN SERIES CURVES     ")
    print("=========================================================")
    
    json_path = os.path.join("clipboard_iterations", "copied_structure.json")
    if not os.path.exists(json_path):
        print(f"[!] Error: Could not find '{json_path}'. Run clipboard analyzer first.")
        return
        
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
        
    unresolved = data.get("unresolved", [])
    
    # 1. Main Title
    title_shape_id = "slide_0b5480b5453b_element_1050_text"
    title_ops = [op for op in unresolved if len(op) > 1 and op[1] == title_shape_id]
    
    # 2. Bounding Rectangles
    rect_ops = [op for op in unresolved if len(op) > 1 and op[0] == 3 and op[2] == 6]
    
    # 3. Light Grey Gridlines (color: #EEEEEE)
    grey_lines = [op for op in unresolved if len(op) > 1 and op[0] == 3 and op[2] == 153 and len(op) > 4 and op[4][7] == "#EEEEEE"]
    
    # 4. Axis Tick Marks and Variable Labels
    tick_shape_ids = set()
    for op in unresolved:
        if op[0] == 15 and op[4] in ["0", "1", "2", "3", "4", "5", "t", "x", "v"]:
            tick_shape_ids.add(op[1])
    tick_ops = [op for op in unresolved if len(op) > 1 and op[1] in tick_shape_ids]
    
    # 5. Sub-graph Headers
    header_texts = ["Stilstand: x(t)", "Stilstand: v(t)", "Constant v: x(t)", "Constant v: v(t)", "Constant a: x(t)", "Constant a: v(t)"]
    header_shape_ids = set()
    for op in unresolved:
        if op[0] == 15 and op[4] in header_texts:
            header_shape_ids.add(op[1])
    header_ops = [op for op in unresolved if len(op) > 1 and op[1] in header_shape_ids]
    
    # 6. Green curves (color: #38761D)
    green_lines = [op for op in unresolved if len(op) > 1 and op[0] == 3 and op[2] == 153 and len(op) > 4 and op[4][7] == "#38761D"]
    
    print(f"[+] Loaded {len(title_ops)} title ops.")
    print(f"[+] Loaded {len(rect_ops)} panel bounding rectangles.")
    print(f"[+] Loaded {len(grey_lines)} light-grey gridlines.")
    print(f"[+] Loaded {len(tick_ops)} tick/axis label ops (across {len(tick_shape_ids)} distinct shapes).")
    print(f"[+] Loaded {len(header_ops)} sub-graph header ops (across {len(header_shape_ids)} distinct shapes).")
    print(f"[+] Loaded {len(green_lines)} green series curve segments.")
    
    # Combine together
    resolved_array = title_ops + rect_ops + grey_lines + tick_ops + header_ops + green_lines
    
    # Register all text shape IDs in autotext_content
    autotext_content = {
        f"{{\"shapeId\":\"{title_shape_id}\"}}": {}
    }
    for tsid in tick_shape_ids:
        autotext_content[f"{{\"shapeId\":\"{tsid}\"}}"] = {}
    for hsid in header_shape_ids:
        autotext_content[f"{{\"shapeId\":\"{hsid}\"}}"] = {}
        
    inner_payload = {
        "resolved": resolved_array,
        "unresolved": resolved_array,
        "autotext_content": autotext_content,
        "did_remove_empty_picture_placeholders": False,
        "copy_source_supports_inheritance_via_master": True
    }
    
    flat_data = json.dumps(inner_payload)
    
    wrapped_payload = {
        "dih": 842511082,
        "data": flat_data,
        "edi": "skypq-BkAfIVRJ0_gJtVM5a3sBPkWr3dhgMrkTdKPjx_R1XRwGgq9K-oMrmEwnjnG5bDzCJYMbXVndL5UrwJdmB3XyZgc3lJvej-sRmk-VYJ",
        "edrk": "aEwPAIfqKbYG1_v8PLTp1p0vXYvowROmaz0UdSS8uKSVqkTiLQ..",
        "dct": "punch",
        "ds": False,
        "cses": False,
        "sm": "other"
    }
    
    wrapped_str = json.dumps(wrapped_payload)
    
    pairs = [
        ("application/x-vnd.google-docs-drawings-object+wrapped", wrapped_str),
        ("application/x-vnd.google-docs-internal-clip-id", "be626f2b-81a1-ab00-1255-47f90648ed96")
    ]
    
    success = set_clipboard_data(pairs, text_fallback="[Google Slides Kinematics Grid Step 5]")
    if success:
        print("\n[+] Success! Grid Step 5 (Step 4 + Green Series) has been written.")
        print("    You can now paste (Ctrl+V) directly onto any active Google Slides slide.")
    else:
        print("\n[!] Error: Failed to write Step 5 payload.")

if __name__ == "__main__":
    main()
