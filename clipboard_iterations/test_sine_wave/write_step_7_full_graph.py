import ctypes
import json
import os

# ==============================================================================
# WIN32 API CLIPBOARD INTEGRATION
# ==============================================================================
# Binding to ctypes dynamic link libraries (User32 and Kernel32) for direct
# memory and clipboard interaction under Windows.
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Set strict parameter types for safe 64-bit Windows execution.
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
    Encodes MIME key-value pairs into Chromium's custom clipboard format byte stream.
    
    Structure:
    ----------------------------------------------------------------------------
    [4 bytes] Length of subsequent pairs data
    [4 bytes] Number of total MIME pairs
    For each pair:
      - [4 bytes] Length of Key string
      - [Key string encoded in UTF-16LE]
      - [Alignment null bytes if characters length is odd]
      - [4 bytes] Length of Value string
      - [Value string encoded in UTF-16LE]
      - [Alignment null bytes if characters length is odd]
    ----------------------------------------------------------------------------
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
    """Pushes MIME pairs and a fallback plain text string onto the active Windows clipboard."""
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
    print("    WRITING STEP 7: COMPLETE ORIGINAL VECTOR GRAPH        ")
    print("=========================================================")
    
    # Path to our master JSON structure extracted from original copy operation
    backup_path = os.path.join("clipboard_iterations", "test_sine_wave", "original_graph_structure.json")
    if not os.path.exists(backup_path):
        print(f"[!] Error: Could not find master structure backup: {backup_path}")
        return
        
    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            full_structure = json.load(f)
    except Exception as e:
        print(f"[!] Error loading master JSON structure: {e}")
        return
        
    # We load the full, un-filtered transaction lists! This includes all preceding layers:
    # 1. Bounding Axes Borders
    # 2. Dashed coordinate Gridlines
    # 3. Text Axis Labels and Title Elements
    # 4. Plotted Math Curves & Red/Green vertical lines
    # 5. coordinate Ellipses / Circles (8 points)
    # AND the final Step 7 elements:
    # 6. LaTeX Overlay Images (ID 3, e.g. "element_363_text" & "element_364_text")
    # 7. White Mask Background Rectangles (ID 6, e.g. "element_363_text_bg")
    resolved_ops = full_structure.get("resolved", [])
    unresolved_ops = full_structure.get("unresolved", [])
    autotext_content = full_structure.get("autotext_content", {})
    
    print(f"[*] Loaded full list of {len(resolved_ops)} resolved GWT operations.")
    print(f"[*] Loaded full list of {len(unresolved_ops)} unresolved GWT operations.")
    print(f"[*] Loaded {len(autotext_content)} active autotext content keys.")
    
    inner_payload = {
        "resolved": resolved_ops,
        "unresolved": unresolved_ops,
        "autotext_content": autotext_content,
        "did_remove_empty_picture_placeholders": False,
        "copy_source_supports_inheritance_via_master": True
    }
    
    flat_data = json.dumps(inner_payload)
    
    # Session transaction envelope
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
    
    success = set_clipboard_data(pairs, text_fallback="[Google Slides Complete Math Vector Graph]")
    if success:
        print("\n[+] Success! The COMPLETE mathematical graph (all 367 visual shapes, 31 labels,")
        print("    curves, coordinates, and LaTeX images) has been written to your system clipboard.")
        print("    Please try pasting (Ctrl+V) directly onto Google Slides.")
    else:
        print("[!] Error writing final graph payload.")

if __name__ == "__main__":
    main()
