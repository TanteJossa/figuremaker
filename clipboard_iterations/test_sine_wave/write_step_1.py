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
    print("    WRITING STEP 1 VERIFIED BASELINE BLUE RECTANGLE      ")
    print("=========================================================")
    
    # Define a single blue rectangle visual element array using GWT "punch" specs.
    # Elements of the shape list:
    # 0: 3 (Operation ID: create/insert)
    # 1: object ID (e.g., "my_custom_rect_01")
    # 2: 6 (Shape Type ID: RECTANGLE)
    # 3: Transform: [scaleX=1.5, skewX=0, skewY=0, scaleY=1.0, tx=15000, ty=15000] (in centipoints)
    # 4: Visual styles: [14, 1 (Solid fill enabled), 15 (Fill), "#cfe2f3" (light blue), 16, 1, 18, 1, 19 (Stroke), "#0b5394" (dark blue), 22 (Weight), 200 (2pt width), 60, 0]
    # 5: "p" (Parent reference)
    resolved_array = [
        [3, "my_custom_rect_01", 6, [1.5, 0, 0, 1.0, 15000, 15000], [14, 1, 15, "#cfe2f3", 16, 1, 18, 1, 19, "#0b5394", 22, 200, 60, 0], "p"]
    ]
    
    # Wrap in inner GWT punch JSON envelope
    inner_payload = {
        "resolved": resolved_array,
        "unresolved": resolved_array,
        "autotext_content": {
            "{\"shapeId\":\"my_custom_rect_01\"}": {}
        },
        "did_remove_empty_picture_placeholders": False,
        "copy_source_supports_inheritance_via_master": True
    }
    
    flat_data = json.dumps(inner_payload)
    
    # Outer wrapping metadata with GWT transaction IDs
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
    
    # Build MIME pairs
    pairs = [
        ("application/x-vnd.google-docs-drawings-object+wrapped", wrapped_str),
        ("application/x-vnd.google-docs-internal-clip-id", "2519a9aa-7fff-ab00-1255-47f90648ed96")
    ]
    
    # Set clipboard data with clear plain text fallback
    success = set_clipboard_data(pairs, text_fallback="[Google Slides Rect V2]")
    
    if success:
        print("\n[+] Verification payload (1-blue-rectangle) has been placed on the system clipboard!")
        print("    You can now paste (Ctrl+V) directly onto any active Google Slides slide canvas.")
    else:
        print("\n[!] Error: Failed to write baseline payload to system clipboard.")

if __name__ == "__main__":
    main()
