import ctypes
import json
import uuid

from slides_builder import SlidesBuilder

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
        if text_fallback:
            text_bytes = (text_fallback + "\0").encode("utf-16le")
            h_text = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_bytes))
            if h_text:
                p_text = kernel32.GlobalLock(h_text)
                if p_text:
                    ctypes.memmove(p_text, text_bytes, len(text_bytes))
                    kernel32.GlobalUnlock(h_text)
                    user32.SetClipboardData(CF_UNICODETEXT, h_text)
        return True
    finally:
        user32.CloseClipboard()


def main():
    image_url = "https://drive.google.com/uc?id=1d4wQ-xMRo-hgWEt_fj50GFAuXvQ_Q-Ps&export=download"
    native_w, native_h = 260, 54
    width_pt, height_pt = 151.87009448818898, 31.54427007874015

    builder = SlidesBuilder(font_family='Ubuntu')
    builder.add_image(
        x=272.4, y=79.5,
        width_pt=width_pt, height_pt=height_pt,
        image_url=image_url,
        native_width_px=native_w, native_height_px=native_h,
        obj_id='slide_test_element_1_text'
    )
    payload = builder.to_punch()

    clip_id = f"2519a9aa-7fff-ab00-1255-{uuid.uuid4().hex[:12]}"

    # Same as the native-url test, but omit the image-clip wrapper entirely.
    pairs = [
        ("application/x-vnd.google-docs-internal-clip-id", clip_id),
        ("application/x-vnd.google-docs-document-slice-clip+wrapped", payload["document_slice_wrapped"]),
        ("application/x-vnd.google-docs-drawings-object+wrapped", payload["wrapped"]),
    ]

    print("Clipboard MIME pairs (no image-clip):")
    for k, v in pairs:
        print(f"  {k}: {len(v)} chars")

    if set_clipboard_data(pairs, text_fallback="LaTeX no image-clip test"):
        print("\nClipboard set without image-clip wrapper. Paste into Google Slides now (Ctrl+V).")
    else:
        print("\nFailed to set clipboard.")


if __name__ == "__main__":
    main()
