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
    print("    WRITING LATEX STEP 1: TITLE + BACKGROUND + 3 FORMULAS")
    print("=========================================================")
    
    # Step 1: Title text element (SHAPE_TYPE_108) + background rectangle + 3 LaTeX SVG formulas
    # Based on analysis of copied_structure.json:
    # - LaTeX/SVG elements use SHAPE_TYPE_3 (ID: 3) with large scale factors
    # - Style key 39 contains Google Drive URL to SVG image
    # - Style key 49 contains s-blob-v1-IMAGE identifier
    # - Background rectangles use SHAPE_TYPE_6 (ID: 6)
    # - Title uses SHAPE_TYPE_108 (ID: 108)
    
    resolved_array = [
        # Title background rectangle (white bg for title text)
        [3, "slide_c1050e194a62_element_1024_text_bg", 6, [0.311, 0, 0, 0.0682, 58187.5507, 53060.6], [14, 1, 15, "#FFFFFF", 18, 0, 22, 381, 60, 0], "slide_c1050e194a62"],
        
        # Title text element (SHAPE_TYPE_108)
        [3, "slide_c1050e194a62_element_1024_text", 108, [1.6933, 0, 0, 0.1905, 81280, 3810], [44, 0, 45, 1], "slide_c1050e194a62"],
        
        # LaTeX formula 1: Background rectangle
        [3, "slide_c1050e194a62_element_1021_text_bg", 6, [0.3779, 0, 0, 0.0779, 170365.7095, 40411.4], [14, 1, 15, "#FFFFFF", 18, 0, 22, 381, 60, 0], "slide_c1050e194a62"],
        
        # LaTeX formula 1: SVG image element (SHAPE_TYPE_3 with Google Drive URL)
        [3, "slide_c1050e194a62_element_1021_text", 3, [296.7308, 0, 0, 296.7498, 138393.336, 40410.7203], [15, "#EEEEEE", 177, 0, 19, "#595959", 22, 381, 39, "https://drive.google.com/uc?id=1d4wQ-xMRo-hgWEt_fj50GFAuXvQ_Q-Ps&export=download", 49, "s-blob-v1-IMAGE-fFuVjqVvxLQ", 8, 260, 9, 54], "slide_c1050e194a62"],
        
        # LaTeX formula 2: Background rectangle
        [3, "slide_c1050e194a62_element_1022_text_bg", 6, [0.4198, 0, 0, 0.0682, 290576, 53060.6], [14, 1, 15, "#FFFFFF", 18, 0, 22, 381, 60, 0], "slide_c1050e194a62"],
        
        # LaTeX formula 2: SVG image element
        [3, "slide_c1050e194a62_element_1022_text", 3, [229.6131, 0, 0, 229.5908, 263595.1818, 53061.2138], [15, "#EEEEEE", 177, 0, 19, "#595959", 22, 381, 39, "https://drive.google.com/uc?id=1LLC4xJtr7xulr3Kjic0to2KA-kpVpzO7&export=download", 49, "s-blob-v1-IMAGE-ilaHMGnPLEY", 8, 336, 9, 55], "slide_c1050e194a62"],
        
        # LaTeX formula 3: Background rectangle
        [3, "slide_c1050e194a62_element_1023_text_bg", 6, [0.311, 0, 0, 0.0682, 58187.5507, 53060.6], [14, 1, 15, "#FFFFFF", 18, 0, 22, 381, 60, 0], "slide_c1050e194a62"],
        
        # LaTeX formula 3: SVG image element
        [3, "slide_c1050e194a62_element_1023_text", 3, [314.898, 0, 0, 314.8889, 58291.9826, 53061.4316], [15, "#EEEEEE", 177, 0, 19, "#595959", 22, 381, 39, "https://drive.google.com/uc?id=1_5mQAYLlB3HHApK5nMinFqOMBIDd6chc&export=download", 49, "s-blob-v1-IMAGE-uP7B1wqq99U", 8, 245, 9, 54], "slide_c1050e194a62"],
        
        # Text insertion operation (type 15) - populates the title text content
        [15, "slide_c1050e194a62_element_1024_text", None, 0, "Lorenz Attractor (X-Z plane projection)"],
        
        # Text formatting operations (type 17) for the title
        [17, "slide_c1050e194a62_element_1024_text", None, 39, 40, [], [12, 2]],
        [17, "slide_c1050e194a62_element_1024_text", None, 0, 40, [], [0, 1, 4, "#0B5394", 5, "Ubuntu", 6, 18]]
    ]
    
    # Wrap in inner GWT punch JSON envelope
    inner_payload = {
        "resolved": resolved_array,
        "unresolved": resolved_array,
        "autotext_content": {
            "{\"shapeId\":\"slide_c1050e194a62_element_1024_text\"}": {}
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
    success = set_clipboard_data(pairs, text_fallback="[Google Slides LaTeX Step 1]")
    
    if success:
        print("\n[+] Step 1 payload (title + 3 LaTeX formulas) has been placed on the system clipboard!")
        print("    Elements included:")
        print("    - Title text: 'Lorenz Attractor (X-Z plane projection)'")
        print("    - 3 LaTeX/SVG formula elements (SHAPE_TYPE_3 with Google Drive URLs)")
        print("    - Background rectangles for each formula")
        print("\n    You can now paste (Ctrl+V) directly onto any active Google Slides slide canvas.")
        print("    Verify that the title and 3 formula SVGs appear correctly positioned.")
    else:
        print("\n[!] Error: Failed to write Step 1 payload to system clipboard.")

if __name__ == "__main__":
    main()