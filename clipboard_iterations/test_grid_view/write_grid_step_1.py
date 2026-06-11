import ctypes
import json

# Win32 clipboard constants and functions
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Define argument and return types for 64-bit Windows safety
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
        # Write Key length (4 bytes) + UTF-16LE characters
        data += len(k).to_bytes(4, "little") + k.encode("utf-16le")
        if len(k) % 2 != 0:
            data += b"\0\0" # alignment padding
            
        # Write Value length (4 bytes) + UTF-16LE characters
        data += len(v).to_bytes(4, "little") + v.encode("utf-16le")
        if len(v) % 2 != 0:
            data += b"\0\0" # alignment padding
            
    # Prepend pair count and total data length
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
        
        # 1. Write custom Chromium format
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
                
        # 2. Write fallback Unicode Text
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
                else:
                    print("[!] Error: Failed to lock text memory.")
            else:
                print("[!] Error: Failed to allocate text memory.")
                    
        return True
    finally:
        user32.CloseClipboard()

def main():
    print("=========================================================")
    print("      WRITING GRID STEP 1: TITLE & 6 OUTER FRAMES        ")
    print("=========================================================")
    
    # 1. Main Title Shape + Text Ops
    title_shape_id = "slide_0b5480b5453b_element_1050_text"
    resolved_array = [
        [3, title_shape_id, 108, [1.6933, 0, 0, 0.2117, 15240, 5080], [44, 0], "slide_0b5480b5453b"],
        [15, title_shape_id, None, 0, "Overzicht van Bewegingstypen (Grid)"],
        [17, title_shape_id, None, 35, 36, [], [12, 1]],
        [17, title_shape_id, None, 0, 36, [], [0, 1, 4, "#0B5394", 5, "Ubuntu", 6, 20]]
    ]
    
    # 2. The 6 Rectangles / Panels
    rect_style = [14, 0, 15, [None, 4], 18, 1, 19, "#000000", 22, 1524, 43, 0, 60, 0]
    rect_ops = [
        [3, "slide_0b5480b5453b_element_0_rect", 6, [0.7197, 0, 0, 0.508, 30480, 35560], rect_style, "slide_0b5480b5453b"],
        [3, "slide_0b5480b5453b_element_24_rect", 6, [0.7197, 0, 0, 0.508, 141448.8528, 35560], rect_style, "slide_0b5480b5453b"],
        [3, "slide_0b5480b5453b_element_48_rect", 6, [0.7197, 0, 0, 0.508, 259080, 35560], rect_style, "slide_0b5480b5453b"],
        [3, "slide_0b5480b5453b_element_72_rect", 6, [0.7197, 0, 0, 0.508, 30480, 124460], rect_style, "slide_0b5480b5453b"],
        [3, "slide_0b5480b5453b_element_96_rect", 6, [0.7197, 0, 0, 0.508, 144780, 124460], rect_style, "slide_0b5480b5453b"],
        [3, "slide_0b5480b5453b_element_120_rect", 6, [0.7197, 0, 0, 0.508, 259080, 124460], rect_style, "slide_0b5480b5453b"]
    ]
    
    resolved_array.extend(rect_ops)
    
    inner_payload = {
        "resolved": resolved_array,
        "unresolved": resolved_array,
        "autotext_content": {
            f"{{\"shapeId\":\"{title_shape_id}\"}}": {}
        },
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
    
    success = set_clipboard_data(pairs, text_fallback="[Google Slides Kinematics Grid Step 1]")
    if success:
        print("\n[+] Success! Grid Step 1 (Title + 6 Panel Frames) has been written to the system clipboard.")
        print("    You can now paste (Ctrl+V) directly onto any active Google Slides slide.")
    else:
        print("\n[!] Error: Failed to write Step 1 payload.")

if __name__ == "__main__":
    main()
