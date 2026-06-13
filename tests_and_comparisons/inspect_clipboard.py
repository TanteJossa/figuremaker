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
user32.EnumClipboardFormats.argtypes = [ctypes.c_uint]
user32.EnumClipboardFormats.restype = ctypes.c_uint
user32.GetClipboardFormatNameW.argtypes = [ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_int]
user32.GetClipboardFormatNameW.restype = ctypes.c_int
user32.GetClipboardData.argtypes = [ctypes.c_uint]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.RegisterClipboardFormatW.argtypes = [ctypes.c_wchar_p]
user32.RegisterClipboardFormatW.restype = ctypes.c_uint

kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_bool
kernel32.GlobalSize.argtypes = [ctypes.c_void_p]
kernel32.GlobalSize.restype = ctypes.c_size_t

CF_UNICODETEXT = 13

# Register Chromium Web Custom format
CF_CHROMIUM_CUSTOM = user32.RegisterClipboardFormatW("Chromium Web Custom MIME Data Format")

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
    # Sometimes data_len can be slightly different from len(bs)-4 due to padding
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

def inspect():
    if not user32.OpenClipboard(None):
        print("Failed to open clipboard")
        return

    try:
        print("--- Active System Clipboard Formats ---")
        fmt = 0
        while True:
            fmt = user32.EnumClipboardFormats(fmt)
            if fmt == 0:
                break
            buf = ctypes.create_unicode_buffer(256)
            res = user32.GetClipboardFormatNameW(fmt, buf, 256)
            name = buf.value or f"Standard Format {fmt}"
            print(f"Format ID: {fmt} - Name: {name}")

        print("\nChecking Chromium Web Custom MIME Data Format...")
        h_data = user32.GetClipboardData(CF_CHROMIUM_CUSTOM)
        if h_data:
            p_data = kernel32.GlobalLock(h_data)
            sz = kernel32.GlobalSize(h_data)
            if p_data:
                try:
                    raw_bytes = ctypes.string_at(p_data, sz)
                    print(f"Read {sz} bytes of raw custom mime data.")
                    pairs = decode_chromium_web_custom(raw_bytes)
                    print(f"Decoded {len(pairs)} custom MIME pairs:")
                    for k, v in pairs:
                        print(f"\n[Key]: {k} (Value length: {len(v)})")
                        try:
                            # Try parsing as JSON to make it pretty
                            js = json.loads(v)
                            print(json.dumps(js, indent=2)[:2000] + ("..." if len(v) > 2000 else ""))
                        except:
                            print(v[:1000] + ("..." if len(v) > 1000 else ""))
                finally:
                    kernel32.GlobalUnlock(h_data)
        else:
            print("Chromium Web Custom MIME Data Format is not present on the clipboard.")

        print("\nChecking CF_UNICODETEXT...")
        h_text = user32.GetClipboardData(CF_UNICODETEXT)
        if h_text:
            p_text = kernel32.GlobalLock(h_text)
            if p_text:
                try:
                    text = ctypes.wstring_at(p_text)
                    print(f"UnicodeText length: {len(text)}")
                    print(f"Content: {text[:500]}...")
                finally:
                    kernel32.GlobalUnlock(h_text)

    finally:
        user32.CloseClipboard()

if __name__ == "__main__":
    inspect()
