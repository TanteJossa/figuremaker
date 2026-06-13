import ctypes
import json
import sys

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
CF_UNICODETEXT = 13
CF_CHROMIUM_CUSTOM = user32.RegisterClipboardFormatW("Chromium Web Custom MIME Data Format")

def encode_u16string(s):
    encoded = s.encode("utf-16le")
    length = len(s)
    result = length.to_bytes(4, "little") + encoded
    if length % 2 != 0:
        result += b"\0\0"
    return result

def encode_chromium_web_custom(pairs):
    data = len(pairs).to_bytes(4, "little")
    for k, v in pairs:
        data += encode_u16string(k) + encode_u16string(v)
    return len(data).to_bytes(4, "little") + data

def set_clipboard(pairs, fallback_text=""):
    raw = encode_chromium_web_custom(pairs)
    if not user32.OpenClipboard(None):
        print("Failed to open clipboard")
        return False
    try:
        user32.EmptyClipboard()
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw))
        if h:
            p = kernel32.GlobalLock(h)
            if p:
                ctypes.memmove(p, raw, len(raw))
                kernel32.GlobalUnlock(h)
                user32.SetClipboardData(CF_CHROMIUM_CUSTOM, h)
                print("Wrote Chromium custom format")
        if fallback_text:
            tb = (fallback_text + "\0").encode("utf-16le")
            ht = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(tb))
            if ht:
                pt = kernel32.GlobalLock(ht)
                if pt:
                    ctypes.memmove(pt, tb, len(tb))
                    kernel32.GlobalUnlock(ht)
                    user32.SetClipboardData(CF_UNICODETEXT, ht)
                    print("Wrote Unicode text fallback")
        return True
    finally:
        user32.CloseClipboard()

def main():
    with open('generated_grid_wrapped.json', 'r', encoding='utf-8') as f:
        wrapped = json.load(f)
    with open('generated_grid_payload.json', 'r', encoding='utf-8') as f:
        inner = json.load(f)

    # Ensure inner payload has required flags
    inner.setdefault('did_remove_empty_picture_placeholders', False)
    inner.setdefault('copy_source_supports_inheritance_via_master', True)
    flat_str = json.dumps(inner, separators=(',', ':'))

    wrapped['data'] = flat_str
    wrapped_str = json.dumps(wrapped, separators=(',', ':'))

    pairs = [
        ("application/x-vnd.google-docs-drawings-object+wrapped", wrapped_str),
        ("application/x-vnd.google-docs-internal-clip-id", "test-grid-clip-001"),
    ]

    if set_clipboard(pairs, fallback_text="[Generated Grid Test]"):
        print("Clipboard set. Please paste into Google Slides.")
    else:
        print("Failed to set clipboard.")

if __name__ == '__main__':
    main()
