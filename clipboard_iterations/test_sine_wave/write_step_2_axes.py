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
    """
    Encodes standard custom MIME type pairs into Chromium's custom format buffer structure.
    """
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
    print("      WRITING STEP 2: OUTER FRAME borders (AXES)         ")
    print("=========================================================")
    
    # These are the four exact borders representing the rectangular bounding frame:
    # Top, bottom, left, and right borders of the coordinate grid.
    # Format of GWT visual path:
    # [3, id, 153 (line), [scaleX, skewX, skewY, scaleY, tx, ty], styles_list, "p"]
    resolved_array = [
        # 1. Bottom Border Line (axes_child_18)
        [
            3,
            "axes_child_18",
            153,
            [2.5823, 0, 0, 0.0004, 40640, 180340],
            [14, 0, 15, "#EEEEEE", 18, 1, 19, "#000000", 22, 1524, 27, 1.3, 30, 1.3, 43, 0],
            "p"
        ],
        # 2. Left Border Line (axes_child_19)
        [
            3,
            "axes_child_19",
            153,
            [0.0004, 0, 0, -1.3335, 40640, 180340],
            [14, 0, 15, "#EEEEEE", 18, 1, 19, "#000000", 22, 1524, 27, 1.3, 30, 1.3, 43, 0],
            "p"
        ],
        # 3. Top Border Line (axes_child_20)
        [
            3,
            "axes_child_20",
            153,
            [2.5823, 0, 0, 0.0004, 40640, 20320],
            [14, 0, 15, "#EEEEEE", 18, 1, 19, "#000000", 22, 1524, 27, 1.3, 30, 1.3, 43, 0],
            "p"
        ],
        # 4. Right Border Line (axes_child_21)
        [
            3,
            "axes_child_21",
            153,
            [0.0004, 0, 0, -1.3335, 350520, 180340],
            [14, 0, 15, "#EEEEEE", 18, 1, 19, "#000000", 22, 1524, 27, 1.3, 30, 1.3, 43, 0],
            "p"
        ]
    ]
    
    inner_payload = {
        "resolved": resolved_array,
        "unresolved": resolved_array,
        "autotext_content": {},
        "did_remove_empty_picture_placeholders": False,
        "copy_source_supports_inheritance_via_master": True
    }
    
    flat_data = json.dumps(inner_payload)
    
    # Wrap in outer envelope with transaction/session keys
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
    
    success = set_clipboard_data(pairs, text_fallback="[Google Slides Bounding Axes]")
    if success:
        print("\n[+] Step 2 payload (4 bounding axes borders) placed on your clipboard.")
        print("    Please paste (Ctrl+V) directly onto Google Slides to test!")
    else:
        print("\n[!] Error writing Step 2 payload.")

if __name__ == "__main__":
    main()
