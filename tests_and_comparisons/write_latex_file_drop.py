import ctypes
import json
import uuid
import os
import struct

from graph_engine import compile_latex_to_png
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
CF_HDROP = 15
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


def make_hdrop(path):
    """Build a DROPFILES structure with a single Unicode file path."""
    path_w = path + "\0\0"
    path_bytes = path_w.encode("utf-16le")
    # DROPFILES header: 20 bytes
    header = struct.pack("<IIIIII", 20, 0, 0, 0, 1, 0)
    return header + path_bytes


def set_clipboard_data(pairs, file_path=None, text_fallback=""):
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
        if file_path:
            hdrop = make_hdrop(file_path)
            h_drop = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(hdrop))
            if h_drop:
                p_drop = kernel32.GlobalLock(h_drop)
                if p_drop:
                    ctypes.memmove(p_drop, hdrop, len(hdrop))
                    kernel32.GlobalUnlock(h_drop)
                    user32.SetClipboardData(CF_HDROP, h_drop)
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
    print("Rendering LaTeX equation x(t) to PNG...")
    latex_meta = compile_latex_to_png(r'x(t)', 16, '#000000', 'center')
    print(json.dumps(latex_meta, indent=2, default=str))

    local_path = latex_meta['local_path']
    from PIL import Image
    with Image.open(local_path) as img:
        native_w, native_h = img.width, img.height
    print(f"PNG dimensions: {native_w}x{native_h}")

    # Copy PNG to a stable file path
    stable_path = os.path.join(os.getcwd(), "latex_test_image.png")
    import shutil
    shutil.copy(local_path, stable_path)
    print(f"PNG saved to: {stable_path}")

    builder = SlidesBuilder(font_family='Ubuntu')
    builder.add_image(
        x=272.4, y=79.5,
        width_pt=latex_meta['width'], height_pt=latex_meta['height'],
        image_url='',  # empty URL; hope Chrome creates filesystem URL from CF_HDROP
        native_width_px=native_w,
        native_height_px=native_h,
        obj_id='slide_test_element_1_text'
    )
    payload = builder.to_punch()

    clip_id = f"2519a9aa-7fff-ab00-1255-{uuid.uuid4().hex[:12]}"
    pairs = [
        ("application/x-vnd.google-docs-internal-clip-id", clip_id),
        ("application/x-vnd.google-docs-drawings-object+wrapped", payload["wrapped"]),
    ]

    print("\nClipboard MIME pairs:")
    for k, v in pairs:
        print(f"  {k}: {len(v)} chars")

    if set_clipboard_data(pairs, file_path=stable_path, text_fallback="LaTeX equation test"):
        print("\nClipboard set (with file drop). Paste into Google Slides now (Ctrl+V).")
    else:
        print("\nFailed to set clipboard.")


if __name__ == "__main__":
    main()
