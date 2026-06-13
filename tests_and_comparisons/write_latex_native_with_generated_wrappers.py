import ctypes
import json
import uuid

from graph_engine import compile_latex_to_png
from slides_builder import SlidesBuilder

# Load the captured native payload.
with open("last_clipboard.json", "r", encoding="utf-8") as f:
    native = json.load(f)

# Build a generated payload so we can steal its wrapper signatures.
drive_url = "https://drive.google.com/uc?id=1d4wQ-xMRo-hgWEt_fj50GFAuXvQ_Q-Ps&export=download"
native_w, native_h = 260, 54
width_pt = 296.7308 * native_w / 508.0
height_pt = 296.7498 * native_h / 508.0

builder = SlidesBuilder(font_family='Ubuntu')
builder.add_image(
    x=138393.336 / 508.0,
    y=40410.7203 / 508.0,
    width_pt=width_pt,
    height_pt=height_pt,
    image_url=drive_url,
    native_width_px=native_w,
    native_height_px=native_h,
    obj_id='slide_c1050e194a62_element_1021_text',
)
gen = builder.to_punch()

def get_meta(wrapped_str):
    w = json.loads(wrapped_str)
    return {k: w[k] for k in ("dih", "edi", "edrk", "dct", "ds", "cses", "sm")}

gen_draw_meta = get_meta(gen["wrapped"])
gen_doc_meta = get_meta(gen["document_slice_wrapped"])
gen_img_meta = get_meta(gen["image_clip_wrapped"])

def apply_meta(native_wrapped, meta):
    if isinstance(native_wrapped, str):
        w = json.loads(native_wrapped)
    else:
        # Avoid modifying original dictionary in-place by copying it
        w = dict(native_wrapped)
    w.update(meta)
    return json.dumps(w, separators=(',', ':'))

# Use native inner data but generated wrapper signatures.
pairs = [
    ("application/x-vnd.google-docs-internal-clip-id", native["application/x-vnd.google-docs-internal-clip-id"]),
    ("application/x-vnd.google-docs-document-slice-clip+wrapped", apply_meta(native["application/x-vnd.google-docs-document-slice-clip+wrapped"], gen_doc_meta)),
    ("application/x-vnd.google-docs-drawings-object+wrapped", apply_meta(native["application/x-vnd.google-docs-drawings-object+wrapped"], gen_draw_meta)),
    ("application/x-vnd.google-docs-image-clip+wrapped", apply_meta(native["application/x-vnd.google-docs-image-clip+wrapped"], gen_img_meta)),
]

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
    print("Testing native inner data with generated wrapper signatures...")
    for k, v in pairs:
        print(f"  {k}: {len(v)} chars")
    if set_clipboard_data(pairs, text_fallback="native data + generated wrappers"):
        print("\nClipboard set. Paste into Google Slides and report the result.")
    else:
        print("\nFailed to set clipboard.")


if __name__ == "__main__":
    main()
