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
        # Write Key length (4 bytes) + UTF-16LE characters
        data += len(k).to_bytes(4, "little") + k.encode("utf-16le")
        if len(k) % 2 != 0:
            data += b"\0\0" # alignment padding if char length is odd
            
        # Write Value length (4 bytes) + UTF-16LE characters
        data += len(v).to_bytes(4, "little") + v.encode("utf-16le")
        if len(v) % 2 != 0:
            data += b"\0\0" # alignment padding if char length is odd
            
    # Prepend pair count and total data length
    total_data = len(pairs).to_bytes(4, "little") + data
    return len(total_data).to_bytes(4, "little") + total_data

def set_clipboard_data(pairs, text_fallback=""):
    """
    Writes custom MIME pairs and a fallback plain text string to the Windows clipboard.
    """
    raw_custom_bytes = encode_chromium_web_custom(pairs)
    
    if not user32.OpenClipboard(None):
        print("[!] Error: Failed to open clipboard.")
        return False
        
    try:
        user32.EmptyClipboard()
        
        # 1. Write the custom Chromium format
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw_custom_bytes))
        if h_mem:
            p_mem = kernel32.GlobalLock(h_mem)
            if p_mem:
                ctypes.memmove(p_mem, raw_custom_bytes, len(raw_custom_bytes))
                kernel32.GlobalUnlock(h_mem)
                user32.SetClipboardData(CF_CHROMIUM_CUSTOM, h_mem)
                print("[+] Successfully wrote Chromium Web Custom MIME Data Format.")
            else:
                print("[!] Error: Failed to lock memory for Custom MIME Format.")
        else:
            print("[!] Error: Failed to allocate memory for Custom MIME Format.")
                
        # 2. Write the fallback Unicode Text format
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
                    print("[!] Error: Failed to lock memory for Unicode Text.")
            else:
                print("[!] Error: Failed to allocate memory for Unicode Text.")
                    
        return True
    finally:
        user32.CloseClipboard()

def main():
    print("=========================================================")
    print("  WRITING LATEX STEP 4: TITLE + FORMULAS + AXES + GRIDLINES + LABELS")
    print("=========================================================")
    
    # Step 4: Title + 3 LaTeX formulas + Axes + 11 Dashed Gridlines + Axis Labels
    # Z-ORDER FIX: Elements are rendered in array order (later = on top)
    # Order: Gridlines -> Axes -> Formulas -> Title (so formulas/axes appear above gridlines)
    
    resolved_array = [
        # === GRIDLINES SECTION (rendered first = at bottom) ===
        # Vertical gridlines (5 lines) - dashed style (key 43 = 2)
        [3, "slide_c1050e194a62_grid_c_jpd6_0", 153, [0.0004, 0, 0, 1.2065, 71120, 33020], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_grid_c_jpd6_1", 153, [0.0004, 0, 0, 1.2065, 132080, 33020], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_grid_c_jpd6_2", 153, [0.0004, 0, 0, 1.2065, 193040, 33020], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_grid_c_jpd6_3", 153, [0.0004, 0, 0, 1.2065, 254000, 33020], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_grid_c_jpd6_4", 153, [0.0004, 0, 0, 1.2065, 314960, 33020], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        
        # Horizontal gridlines (6 lines) - dashed style (key 43 = 2)
        [3, "slide_c1050e194a62_grid_c_jpd6_5", 153, [2.54, 0, 0, 0.0004, 40640, 165735], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_grid_c_jpd6_6", 153, [2.54, 0, 0, 0.0004, 40640, 141605], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_grid_c_jpd6_7", 153, [2.54, 0, 0, 0.0004, 40640, 117475], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_grid_c_jpd6_8", 153, [2.54, 0, 0, 0.0004, 40640, 93345], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_grid_c_jpd6_9", 153, [2.54, 0, 0, 0.0004, 40640, 69215], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_grid_c_jpd6_10", 153, [2.54, 0, 0, 0.0004, 40640, 45085], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#DDDDDD", 22, 508, 27, 1.3, 30, 1.3, 43, 2], "slide_c1050e194a62"],
        
        # Gridlines grouping
        [2, "slide_c1050e194a62_g_grid_jpd6", ["slide_c1050e194a62_grid_c_jpd6_0", "slide_c1050e194a62_grid_c_jpd6_1", "slide_c1050e194a62_grid_c_jpd6_2", "slide_c1050e194a62_grid_c_jpd6_3", "slide_c1050e194a62_grid_c_jpd6_4", "slide_c1050e194a62_grid_c_jpd6_5", "slide_c1050e194a62_grid_c_jpd6_6", "slide_c1050e194a62_grid_c_jpd6_7", "slide_c1050e194a62_grid_c_jpd6_8", "slide_c1050e194a62_grid_c_jpd6_9", "slide_c1050e194a62_grid_c_jpd6_10"], [1, 0, 0, 1, 0, 0], "slide_c1050e194a62"],
        
        # === AXES SECTION (rendered after gridlines = above gridlines) ===
        [3, "slide_c1050e194a62_axes_child_0", 153, [2.6035, 0, 0, 0.0004, 40640, 165735], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#000000", 22, 1270, 27, 1.3, 29, 7, 30, 1.3], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_axes_child_1", 153, [0.0004, 0, 0, -1.27, 193040, 177800], [14, 0, 15, "#EEEEEE", 18, 1, 19, "#000000", 22, 1270, 27, 1.3, 29, 7, 30, 1.3], "slide_c1050e194a62"],
        [2, "slide_c1050e194a62_axes_group", ["slide_c1050e194a62_axes_child_0", "slide_c1050e194a62_axes_child_1"], [1, 0, 0, 1, 0, 0], "slide_c1050e194a62"],
        
        # === AXIS LABELS SECTION (NEW in Step 4) - CORRECTED FORMAT ===
        # X-axis labels (bottom): -20, -10, 10, 20
        [3, "slide_c1050e194a62_element_15_text", 108, [0.254, 0, 0, 0.1016, 55880, 169799], [44, 0, 45, 1], "slide_c1050e194a62"],
        [15, "slide_c1050e194a62_element_15_text", None, 0, "-20"],
        [17, "slide_c1050e194a62_element_15_text", None, 3, 4, [], [12, 2]],
        [17, "slide_c1050e194a62_element_15_text", None, 0, 4, [], [5, "Ubuntu", 6, 16]],
        
        [3, "slide_c1050e194a62_element_16_text", 108, [0.254, 0, 0, 0.1016, 116840, 169799], [44, 0, 45, 1], "slide_c1050e194a62"],
        [15, "slide_c1050e194a62_element_16_text", None, 0, "-10"],
        [17, "slide_c1050e194a62_element_16_text", None, 3, 4, [], [12, 2]],
        [17, "slide_c1050e194a62_element_16_text", None, 0, 4, [], [5, "Ubuntu", 6, 16]],
        
        [3, "slide_c1050e194a62_element_17_text", 108, [0.254, 0, 0, 0.1016, 238760, 169799], [44, 0, 45, 1], "slide_c1050e194a62"],
        [15, "slide_c1050e194a62_element_17_text", None, 0, "10"],
        [17, "slide_c1050e194a62_element_17_text", None, 2, 3, [], [12, 2]],
        [17, "slide_c1050e194a62_element_17_text", None, 0, 3, [], [5, "Ubuntu", 6, 16]],
        
        [3, "slide_c1050e194a62_element_18_text", 108, [0.254, 0, 0, 0.1016, 299720, 169799], [44, 0, 45, 1], "slide_c1050e194a62"],
        [15, "slide_c1050e194a62_element_18_text", None, 0, "20"],
        [17, "slide_c1050e194a62_element_18_text", None, 2, 3, [], [12, 2]],
        [17, "slide_c1050e194a62_element_18_text", None, 0, 3, [], [5, "Ubuntu", 6, 16]],
        
        # Y-axis labels (right side): 10, 20, 30, 40, 50
        [3, "slide_c1050e194a62_element_19_text", 108, [0.254, 0, 0, 0.1016, 154940, 135509], [44, 0, 45, 1], "slide_c1050e194a62"],
        [15, "slide_c1050e194a62_element_19_text", None, 0, "10"],
        [17, "slide_c1050e194a62_element_19_text", None, 2, 3, [], [12, 3]],
        [17, "slide_c1050e194a62_element_19_text", None, 0, 3, [], [5, "Ubuntu", 6, 16]],
        
        [3, "slide_c1050e194a62_element_20_text", 108, [0.254, 0, 0, 0.1016, 154940, 111379], [44, 0, 45, 1], "slide_c1050e194a62"],
        [15, "slide_c1050e194a62_element_20_text", None, 0, "20"],
        [17, "slide_c1050e194a62_element_20_text", None, 2, 3, [], [12, 3]],
        [17, "slide_c1050e194a62_element_20_text", None, 0, 3, [], [5, "Ubuntu", 6, 16]],
        
        [3, "slide_c1050e194a62_element_21_text", 108, [0.254, 0, 0, 0.1016, 154940, 87249], [44, 0, 45, 1], "slide_c1050e194a62"],
        [15, "slide_c1050e194a62_element_21_text", None, 0, "30"],
        [17, "slide_c1050e194a62_element_21_text", None, 2, 3, [], [12, 3]],
        [17, "slide_c1050e194a62_element_21_text", None, 0, 3, [], [5, "Ubuntu", 6, 16]],
        
        [3, "slide_c1050e194a62_element_22_text", 108, [0.254, 0, 0, 0.1016, 154940, 63119], [44, 0, 45, 1], "slide_c1050e194a62"],
        [15, "slide_c1050e194a62_element_22_text", None, 0, "40"],
        [17, "slide_c1050e194a62_element_22_text", None, 2, 3, [], [12, 3]],
        [17, "slide_c1050e194a62_element_22_text", None, 0, 3, [], [5, "Ubuntu", 6, 16]],
        
        [3, "slide_c1050e194a62_element_23_text", 108, [0.254, 0, 0, 0.1016, 154940, 38989], [44, 0, 45, 1], "slide_c1050e194a62"],
        [15, "slide_c1050e194a62_element_23_text", None, 0, "50"],
        [17, "slide_c1050e194a62_element_23_text", None, 2, 3, [], [12, 3]],
        [17, "slide_c1050e194a62_element_23_text", None, 0, 3, [], [5, "Ubuntu", 6, 16]],
        
        # === LATEX FORMULAS SECTION (rendered after axes = above axes) ===
        [3, "slide_c1050e194a62_element_1021_text_bg", 6, [0.3779, 0, 0, 0.0779, 170365.7095, 40411.4], [14, 1, 15, "#FFFFFF", 18, 0, 22, 381, 60, 0], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_element_1021_text", 3, [296.7308, 0, 0, 296.7498, 138393.336, 40410.7203], [15, "#EEEEEE", 177, 0, 19, "#595959", 22, 381, 39, "https://drive.google.com/uc?id=1d4wQ-xMRo-hgWEt_fj50GFAuXvQ_Q-Ps&export=download", 49, "s-blob-v1-IMAGE-fFuVjqVvxLQ", 8, 260, 9, 54], "slide_c1050e194a62"],
        
        [3, "slide_c1050e194a62_element_1022_text_bg", 6, [0.4198, 0, 0, 0.0682, 290576, 53060.6], [14, 1, 15, "#FFFFFF", 18, 0, 22, 381, 60, 0], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_element_1022_text", 3, [229.6131, 0, 0, 229.5908, 263595.1818, 53061.2138], [15, "#EEEEEE", 177, 0, 19, "#595959", 22, 381, 39, "https://drive.google.com/uc?id=1LLC4xJtr7xulr3Kjic0to2KA-kpVpzO7&export=download", 49, "s-blob-v1-IMAGE-ilaHMGnPLEY", 8, 336, 9, 55], "slide_c1050e194a62"],
        
        [3, "slide_c1050e194a62_element_1023_text_bg", 6, [0.311, 0, 0, 0.0682, 58187.5507, 53060.6], [14, 1, 15, "#FFFFFF", 18, 0, 22, 381, 60, 0], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_element_1023_text", 3, [314.898, 0, 0, 314.8889, 58291.9826, 53061.4316], [15, "#EEEEEE", 177, 0, 19, "#595959", 22, 381, 39, "https://drive.google.com/uc?id=1_5mQAYLlB3HHApK5nMinFqOMBIDd6chc&export=download", 49, "s-blob-v1-IMAGE-uP7B1wqq99U", 8, 245, 9, 54], "slide_c1050e194a62"],
        
        # === TITLE SECTION (rendered last = on top) ===
        [3, "slide_c1050e194a62_element_1024_text_bg", 6, [0.311, 0, 0, 0.0682, 58187.5507, 53060.6], [14, 1, 15, "#FFFFFF", 18, 0, 22, 381, 60, 0], "slide_c1050e194a62"],
        [3, "slide_c1050e194a62_element_1024_text", 108, [1.6933, 0, 0, 0.1905, 81280, 3810], [44, 0, 45, 1], "slide_c1050e194a62"],
        [15, "slide_c1050e194a62_element_1024_text", None, 0, "Lorenz Attractor (X-Z plane projection)"],
        [17, "slide_c1050e194a62_element_1024_text", None, 39, 40, [], [12, 2]],
        [17, "slide_c1050e194a62_element_1024_text", None, 0, 40, [], [0, 1, 4, "#0B5394", 5, "Ubuntu", 6, 18]]
    ]
    
    # Wrap in inner GWT punch JSON envelope
    inner_payload = {
        "resolved": resolved_array,
        "unresolved": resolved_array,
        "autotext_content": {
            "{\"shapeId\":\"slide_c1050e194a62_element_1024_text\"}": {},
            "{\"shapeId\":\"slide_c1050e194a62_element_15_text\"}": {},
            "{\"shapeId\":\"slide_c1050e194a62_element_16_text\"}": {},
            "{\"shapeId\":\"slide_c1050e194a62_element_17_text\"}": {},
            "{\"shapeId\":\"slide_c1050e194a62_element_18_text\"}": {},
            "{\"shapeId\":\"slide_c1050e194a62_element_19_text\"}": {},
            "{\"shapeId\":\"slide_c1050e194a62_element_20_text\"}": {},
            "{\"shapeId\":\"slide_c1050e194a62_element_21_text\"}": {},
            "{\"shapeId\":\"slide_c1050e194a62_element_22_text\"}": {},
            "{\"shapeId\":\"slide_c1050e194a62_element_23_text\"}": {}
        },
        "did_remove_empty_picture_placeholders": False,
        "copy_source_supports_inheritance_via_master": True
    }
    
    flat_data = json.dumps(inner_payload)
    
    # Outer wrapping metadata with GWT transaction IDs (from original capture)
    wrapped_payload = {
        "dih": 842511082,
        "data": flat_data,
        "edi": "vyVruLiFLprc-j1zpZg0uM72sAOTSjGWiVQanfjm1DEvKBqZyeXYlUaGMnmnDnXcIEuJquWxmFVoGex3KFtVgvPaiY8eghTib5jOQ72-lFGf",
        "edrk": "nBCrylrRJCls02yVORKWoWzDsW5ToXhvPahuaqxLzsuP-TsHWw..",
        "dct": "punch",
        "ds": False,
        "cses": False,
        "sm": "other"
    }
    
    wrapped_str = json.dumps(wrapped_payload)
    
    # Build MIME pairs
    pairs = [
        ("application/x-vnd.google-docs-drawings-object+wrapped", wrapped_str),
        ("application/x-vnd.google-docs-internal-clip-id", "2519a9aa-7fff-ab00-1255-47f90648ed96")
    ]
    
    # Set clipboard data with clear plain text fallback
    success = set_clipboard_data(pairs, text_fallback="[Google Slides LaTeX Step 4 - Labels]")
    
    if success:
        print("\n[+] Step 4 payload (Title + 3 LaTeX formulas + Axes + Gridlines + Labels) has been placed on the system clipboard!")
        print("    Elements included:")
        print("    - 11 Dashed gridlines (at bottom z-order)")
        print("    - X-Axis and Y-Axis (above gridlines)")
        print("    - 9 Axis labels: X-axis (-20, -10, 10, 20), Y-axis (10, 20, 30, 40, 50)")
        print("    - 3 LaTeX/SVG formula elements (above axes)")
        print("    - Title text (on top)")
        print("\n    Z-ORDER FIX: Gridlines rendered first, formulas/axes rendered later")
        print("    You can now paste (Ctrl+V) directly onto any active Google Slides slide canvas.")
    else:
        print("\n[!] Error: Failed to write Step 4 payload to system clipboard.")

if __name__ == "__main__":
    main()