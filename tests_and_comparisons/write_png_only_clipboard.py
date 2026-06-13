import ctypes
import io
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
CF_PNG = user32.RegisterClipboardFormatW("PNG")
CF_DIBV5 = 17


def png_to_dibv5(png_bytes):
    """Convert PNG bytes to a CF_DIBV5 bitmap (BGRA with BITMAPV5HEADER)."""
    img = Image.open(io.BytesIO(png_bytes))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    width, height = img.size

    # BITMAPV5HEADER size = 124 bytes
    header_size = 124
    row_size = ((width * 32 + 31) // 32) * 4
    pixel_data_size = row_size * height
    total_size = header_size + pixel_data_size

    buf = bytearray(total_size)

    # BITMAPV5HEADER fields (little-endian)
    import struct
    struct.pack_into('<I', buf, 0, header_size)
    struct.pack_into('<i', buf, 4, width)
    struct.pack_into('<i', buf, 8, height)
    struct.pack_into('<H', buf, 12, 1)   # planes
    struct.pack_into('<H', buf, 14, 32)  # bit count
    struct.pack_into('<I', buf, 16, 0)   # compression = BI_RGB
    struct.pack_into('<I', buf, 20, pixel_data_size)
    struct.pack_into('<i', buf, 24, 2835)  # X ppm
    struct.pack_into('<i', buf, 28, 2835)  # Y ppm
    struct.pack_into('<I', buf, 32, 0)   # clr used
    struct.pack_into('<I', buf, 36, 0)   # clr important
    struct.pack_into('<I', buf, 40, 0x00FF0000)  # R mask
    struct.pack_into('<I', buf, 44, 0x0000FF00)  # G mask
    struct.pack_into('<I', buf, 48, 0x000000FF)  # B mask
    struct.pack_into('<I', buf, 52, 0xFF000000)  # A mask
    struct.pack_into('<I', buf, 56, 0x73524742)  # color space 'sRGB'

    pixels = img.transpose(Image.FLIP_TOP_BOTTOM).tobytes()
    # PIL RGBA is R,G,B,A. DIBV5 expects B,G,R,A.
    dst_offset = header_size
    for y in range(height):
        src_row_start = y * width * 4
        for x in range(width):
            src = src_row_start + x * 4
            r, g, b, a = pixels[src], pixels[src+1], pixels[src+2], pixels[src+3]
            dst = dst_offset + y * row_size + x * 4
            buf[dst] = b
            buf[dst+1] = g
            buf[dst+2] = r
            buf[dst+3] = a

    return bytes(buf)


def main():
    from graph_engine import compile_latex_to_png
    latex_meta = compile_latex_to_png(r'x(t)', 16, '#000000', 'center')
    local_path = latex_meta['local_path']

    with open(local_path, 'rb') as f:
        png_bytes = f.read()

    print(f"PNG size: {len(png_bytes)} bytes, dimensions: {latex_meta['width']}x{latex_meta['height']} pt")

    if not user32.OpenClipboard(None):
        print("Failed to open clipboard")
        return

    user32.EmptyClipboard()

    # PNG format
    h_png = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(png_bytes))
    if h_png:
        p_png = kernel32.GlobalLock(h_png)
        if p_png:
            ctypes.memmove(p_png, png_bytes, len(png_bytes))
            kernel32.GlobalUnlock(h_png)
            user32.SetClipboardData(CF_PNG, h_png)

    # DIBV5 format
    dibv5 = png_to_dibv5(png_bytes)
    h_dib = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(dibv5))
    if h_dib:
        p_dib = kernel32.GlobalLock(h_dib)
        if p_dib:
            ctypes.memmove(p_dib, dibv5, len(dibv5))
            kernel32.GlobalUnlock(h_dib)
            user32.SetClipboardData(CF_DIBV5, h_dib)

    user32.CloseClipboard()
    print("PNG + DIBV5 bytes written to clipboard. Paste into Google Slides.")


if __name__ == "__main__":
    main()
