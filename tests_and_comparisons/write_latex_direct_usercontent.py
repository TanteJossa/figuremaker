import ctypes
import json
import uuid
import os

from graph_engine import compile_latex_to_png
from slides_builder import SlidesBuilder
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

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
CF_CUSTOM = user32.RegisterClipboardFormatW("Chromium Web Custom MIME Data Format")


def encode_chromium_web_custom(pairs):
    data = b""
    for k, v in pairs:
        data += len(k).to_bytes(4, "little") + k.encode("utf-16le")
        if len(k) % 2 != 0:
            data += b"\0\0"
        data += len(v).to_bytes(4, "little") + v.encode("utf-16le")
        if len(v) % 2 != 0:
            data += b"\0\0"
    total = len(pairs).to_bytes(4, "little") + data
    return len(total).to_bytes(4, "little") + total


def set_clipboard_data(pairs):
    raw = encode_chromium_web_custom(pairs)
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw))
        if h:
            p = kernel32.GlobalLock(h)
            if p:
                ctypes.memmove(p, raw, len(raw))
                kernel32.GlobalUnlock(h)
                user32.SetClipboardData(CF_CUSTOM, h)
        return True
    finally:
        user32.CloseClipboard()


def main():
    print("Rendering LaTeX equation x(t) to PNG...")
    latex_meta = compile_latex_to_png(r'x(t)', 16, '#000000', 'center')
    local_path = latex_meta['local_path']
    with Image.open(local_path) as img:
        native_w, native_h = img.width, img.height
    print(f"PNG dimensions: {native_w}x{native_h}")

    creds = Credentials.from_authorized_user_file('token.json')
    service = build('drive', 'v3', credentials=creds)
    drive_file = service.files().create(
        body={'name': os.path.basename(local_path), 'mimeType': 'image/png'},
        media_body=MediaFileUpload(local_path, mimetype='image/png'),
        fields='id'
    ).execute()
    file_id = drive_file['id']
    service.permissions().create(fileId=file_id, body={'role': 'reader', 'type': 'anyone'}).execute()

    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download"
    print(f"Direct URL: {url}")

    builder = SlidesBuilder()
    builder.add_image(
        x=272.4, y=79.5,
        width_pt=latex_meta['width'], height_pt=latex_meta['height'],
        image_url=url,
        native_width_px=native_w, native_height_px=native_h,
        obj_id='slide_test_element_1_text'
    )
    payload = builder.to_punch()

    clip_id = f"2519a9aa-7fff-ab00-1255-{uuid.uuid4().hex[:12]}"
    set_clipboard_data([
        ("application/x-vnd.google-docs-internal-clip-id", clip_id),
        ("application/x-vnd.google-docs-document-slice-clip+wrapped", payload["document_slice_wrapped"]),
        ("application/x-vnd.google-docs-drawings-object+wrapped", payload["wrapped"]),
        ("application/x-vnd.google-docs-image-clip+wrapped", payload["image_clip_wrapped"]),
    ])
    print("Clipboard set with direct usercontent URL. Paste into Google Slides.")


if __name__ == "__main__":
    main()
