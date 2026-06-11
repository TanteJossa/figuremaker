import ctypes
import json

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
user32.GetClipboardData.argtypes = [ctypes.c_uint]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.RegisterClipboardFormatW.argtypes = [ctypes.c_wchar_p]
user32.RegisterClipboardFormatW.restype = ctypes.c_uint

kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_bool
kernel32.GlobalSize.argtypes = [ctypes.c_void_p]
kernel32.GlobalSize.restype = ctypes.c_size_t

GMEM_MOVEABLE = 0x0002
CF_CHROMIUM_CUSTOM = user32.RegisterClipboardFormatW("Chromium Web Custom MIME Data Format")
CF_UNICODETEXT = 13

def read_u16string(bs):
    if len(bs) < 4:
        return "", b""
    length = int.from_bytes(bs[:4], "little")
    byte_length = length * 2
    if length % 2 != 0:
        byte_length += 2
    if len(bs) < 4 + length * 2:
        return "", b""
    text = bs[4 : 4 + length * 2].decode("utf-16le", errors="replace")
    return text, bs[4 + byte_length :]

def decode_chromium_web_custom(bs):
    if len(bs) < 8:
        return []
    data_len = int.from_bytes(bs[:4], "little")
    data = bs[4 : 4 + data_len]
    if len(data) < 4:
        return []
    count = int.from_bytes(data[:4], "little")
    data = data[4:]
    pairs = []
    for _ in range(count):
        if len(data) < 4:
            break
        key, data = read_u16string(data)
        value, data = read_u16string(data)
        pairs.append((key, value))
    return pairs

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

def main():
    if not user32.OpenClipboard(None):
        print("Failed to open clipboard")
        return

    try:
        h_data = user32.GetClipboardData(CF_CHROMIUM_CUSTOM)
        if not h_data:
            print("Chromium Web Custom MIME format not found on clipboard.")
            return
            
        p_data = kernel32.GlobalLock(h_data)
        sz = kernel32.GlobalSize(h_data)
        if not p_data:
            print("Failed to lock global memory.")
            return
            
        pairs = []
        try:
            raw_bytes = ctypes.string_at(p_data, sz)
            pairs = decode_chromium_web_custom(raw_bytes)
        finally:
            kernel32.GlobalUnlock(h_data)
    finally:
        user32.CloseClipboard()

    # Parse and extract
    custom_dict = {k: v for k, v in pairs}
    
    # Extract keys
    drawings_wrapped_str = custom_dict.get("application/x-vnd.google-docs-drawings-object+wrapped")
    if not drawings_wrapped_str:
        print("No drawings wrapped payload on clipboard.")
        return
        
    try:
        wrapped_json = json.loads(drawings_wrapped_str)
    except Exception as e:
        print(f"Failed to parse drawings wrapped JSON: {e}")
        return
        
    print("\n--- Extracted Keys ---")
    print(f"dih: {wrapped_json.get('dih')}")
    print(f"edi: {wrapped_json.get('edi')}")
    print(f"edrk: {wrapped_json.get('edrk')}")
    print(f"clip-id: {custom_dict.get('application/x-vnd.google-docs-internal-clip-id')}")
    
    # Synthesize new blue rectangle payload
    resolved_array = [
        [3, "my_custom_rect_01", 6, [1.5, 0, 0, 1.0, 15000, 15000], [15, "#cfe2f3", 19, "#0b5394", 22, 200], "p"]
    ]
    
    inner_payload = {
        "resolved": resolved_array,
        "unresolved": resolved_array,
        "autotext_content": {},
        "did_remove_empty_picture_placeholders": False,
        "copy_source_supports_inheritance_via_master": True
    }
    
    new_flat_data = json.dumps(inner_payload)
    
    # Re-wrap using their active tokens!
    new_wrapped_payload = {
        "dih": wrapped_json.get("dih", 1245482604),
        "data": new_flat_data,
        "edi": wrapped_json.get("edi"),
        "edrk": wrapped_json.get("edrk"),
        "dct": "punch",
        "ds": False,
        "cses": False,
        "sm": "other"
    }
    
    new_wrapped_str = json.dumps(new_wrapped_payload)
    
    # Build pairs
    new_pairs = [
        ("application/x-vnd.google-docs-drawings-object+wrapped", new_wrapped_str),
        ("application/x-vnd.google-docs-internal-clip-id", custom_dict.get("application/x-vnd.google-docs-internal-clip-id", "2519a9aa-7fff-ab00-1255-47f90648ed96"))
    ]
    
    # Write back to clipboard
    raw_custom_bytes = encode_chromium_web_custom(new_pairs)
    
    if not user32.OpenClipboard(None):
        print("Failed to open clipboard to write.")
        return
        
    try:
        user32.EmptyClipboard()
        
        # Write Chromium Custom
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw_custom_bytes))
        if h_mem:
            p_mem = kernel32.GlobalLock(h_mem)
            if p_mem:
                ctypes.memmove(p_mem, raw_custom_bytes, len(raw_custom_bytes))
                kernel32.GlobalUnlock(h_mem)
                user32.SetClipboardData(CF_CHROMIUM_CUSTOM, h_mem)
                
        # Write text fallback
        text_bytes = ("[Google Slides Rect]\0").encode("utf-16le")
        h_text = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_bytes))
        if h_text:
            p_text = kernel32.GlobalLock(h_text)
            if p_text:
                ctypes.memmove(p_text, text_bytes, len(text_bytes))
                kernel32.GlobalUnlock(h_text)
                user32.SetClipboardData(CF_UNICODETEXT, h_text)
                
        print("\nSuccessfully updated clipboard with 1 Blue Rectangle using active session keys!")
        print("Please go to Google Slides and press Ctrl+V to paste!")
    finally:
        user32.CloseClipboard()

if __name__ == "__main__":
    main()
