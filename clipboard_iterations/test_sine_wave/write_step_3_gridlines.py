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
    print("      WRITING STEP 3: OUTER FRAME + GRIDLINES (DASHED)   ")
    print("=========================================================")
    
    # Gridline styling uses:
    # - stroke color '#DDDDDD' (light grey)
    # - stroke width 508 centipoints (0.5 pt)
    # - Key 43 with value 2 (dashed line style)
    #
    # Bounding borders styling uses:
    # - stroke color '#000000' (black)
    # - stroke width 1524 centipoints (1.5 pt)
    # - Key 43 with value 0 (solid line style)
    
    resolved_array = [
        # --- VERTICAL DASHED GRIDLINES ---
        [3, "axes_child_0", 153, [0.0004, 0, 0, 1.3335, 66463.3333, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_1", 153, [0.0004, 0, 0, 1.3335, 92286.6667, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_2", 153, [0.0004, 0, 0, 1.3335, 118110, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_3", 153, [0.0004, 0, 0, 1.3335, 143933.3333, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_4", 153, [0.0004, 0, 0, 1.3335, 169756.6667, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_5", 153, [0.0004, 0, 0, 1.3335, 195580, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_6", 153, [0.0004, 0, 0, 1.3335, 221403.3333, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_7", 153, [0.0004, 0, 0, 1.3335, 247226.6667, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_8", 153, [0.0004, 0, 0, 1.3335, 273050, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_9", 153, [0.0004, 0, 0, 1.3335, 298873.3333, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_10", 153, [0.0004, 0, 0, 1.3335, 324696.6667, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        
        # --- HORIZONTAL DASHED GRIDLINES ---
        [3, "axes_child_11", 153, [2.5823, 0, 0, 0.0004, 40640, 160337.5], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_12", 153, [2.5823, 0, 0, 0.0004, 40640, 140335], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_13", 153, [2.5823, 0, 0, 0.0004, 40640, 120332.5], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_14", 153, [2.5823, 0, 0, 0.0004, 40640, 100330], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_15", 153, [2.5823, 0, 0, 0.0004, 40640, 80327.5], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_16", 153, [2.5823, 0, 0, 0.0004, 40640, 60325], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        [3, "axes_child_17", 153, [2.5823, 0, 0, 0.0004, 40640, 40322.5], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "p"],
        
        # --- SOLID BOUNDING BORDERS ---
        [3, "axes_child_18", 153, [2.5823, 0, 0, 0.0004, 40640, 180340], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#000000", 22, 1524, 27, 1.3, 30, 1.3, 43, 0], "p"],
        [3, "axes_child_19", 153, [0.0004, 0, 0, -1.3335, 40640, 180340], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#000000", 22, 1524, 27, 1.3, 30, 1.3, 43, 0], "p"],
        [3, "axes_child_20", 153, [2.5823, 0, 0, 0.0004, 40640, 20320], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#000000", 22, 1524, 27, 1.3, 30, 1.3, 43, 0], "p"],
        [3, "axes_child_21", 153, [0.0004, 0, 0, -1.3335, 350520, 180340], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#000000", 22, 1524, 27, 1.3, 30, 1.3, 43, 0], "p"]
    ]
    
    inner_payload = {
        "resolved": resolved_array,
        "unresolved": resolved_array,
        "autotext_content": {},
        "did_remove_empty_picture_placeholders": False,
        "copy_source_supports_inheritance_via_master": True
    }
    
    flat_data = json.dumps(inner_payload)
    
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
    
    success = set_clipboard_data(pairs, text_fallback="[Google Slides Bounding Axes + Grid]")
    if success:
        print("\n[+] Step 3 payload (Borders + dashed gridlines) placed on your clipboard.")
        print("    Please paste (Ctrl+V) directly onto Google Slides to test!")
    else:
        print("\n[!] Error writing Step 3 payload.")

if __name__ == "__main__":
    main()
