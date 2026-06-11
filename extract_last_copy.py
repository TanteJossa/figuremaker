import ctypes
import json

# Win32 clipboard constants and functions
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = ctypes.c_bool
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = ctypes.c_bool
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
            
        try:
            raw_bytes = ctypes.string_at(p_data, sz)
            pairs = decode_chromium_web_custom(raw_bytes)
            
            output = {}
            for k, v in pairs:
                try:
                    output[k] = json.loads(v)
                except:
                    output[k] = v
                    
            with open("last_clipboard.json", "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2)
                
            print(f"Successfully extracted {len(pairs)} keys to last_clipboard.json")
            for k in output.keys():
                print(f"- {k}")
        finally:
            kernel32.GlobalUnlock(h_data)
    finally:
        user32.CloseClipboard()

if __name__ == "__main__":
    main()
