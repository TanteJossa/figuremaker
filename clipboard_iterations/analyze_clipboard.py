import ctypes
import json
import os
import sys

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
CF_CHROMIUM_CUSTOM_NAME = "Chromium Web Custom MIME Data Format"
CF_CHROMIUM_CUSTOM = user32.RegisterClipboardFormatW(CF_CHROMIUM_CUSTOM_NAME)

# Maps common GWT shape IDs to human-readable names
SHAPE_TYPE_MAP = {
    0: "UNKNOWN_SHAPE",
    4: "ELLIPSE",
    5: "TRIANGLE",
    6: "RECTANGLE",
    7: "ROUNDED_RECTANGLE",
    12: "LINE",
    14: "POLYGON",
    23: "RIGHT_ARROW",
    33: "TEXT_BOX",
}

# Maps GWT punch visual style keys to their meanings
STYLE_KEY_MAP = {
    14: "Style Prefix / Option",
    15: "Fill Background Color",
    19: "Stroke Outline Color",
    22: "Stroke Weight (centipoints)",
}

def read_u16string(bs):
    """
    Decodes a length-prefixed UTF-16LE string from a byte stream.
    The first 4 bytes represent the string length (number of wide characters).
    Returns the decoded string and the remaining bytes.
    """
    if len(bs) < 4:
        return "", b""
    length = int.from_bytes(bs[:4], "little")
    byte_length = length * 2
    # Windows clipboard Chromium custom formats sometimes feature word alignment padding
    padding = 2 if length % 2 != 0 else 0
    total_len = 4 + byte_length + padding
    if len(bs) < 4 + byte_length:
        return "", b""
    text = bs[4 : 4 + byte_length].decode("utf-16le", errors="replace")
    return text, bs[total_len:]

def decode_chromium_web_custom(bs):
    """
    Decodes the binary structure of the Chromium Web Custom MIME Data Format.
    The layout is:
    [4 bytes total data length]
    [4 bytes pairs count]
    For each pair:
      [4 bytes key string length] + [UTF-16LE key bytes] + [optional padding]
      [4 bytes value string length] + [UTF-16LE value bytes] + [optional padding]
    """
    if len(bs) < 8:
        return []
    data_len = int.from_bytes(bs[:4], "little")
    # Buffer slice containing the actual pairs
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

def parse_styling_list(style_list):
    """
    Extracts key-value style attributes from flat GWT lists like:
    [14, 0, 15, "#cfe2f3", 19, "#0b5394", 22, 200]
    """
    styles = {}
    i = 0
    while i < len(style_list):
        key = style_list[i]
        if isinstance(key, int) and i + 1 < len(style_list):
            val = style_list[i + 1]
            styles[key] = val
            i += 2
        else:
            i += 1
    return styles

def format_style_summary(styles):
    """Formats style attributes into a clear human-readable list."""
    summary_lines = []
    for k, v in styles.items():
        name = STYLE_KEY_MAP.get(k, f"Style Key {k}")
        if k == 22: # Stroke Weight in centipoints
            summary_lines.append(f"      - {name}: {v / 100:.2f} pt ({v} centipoints)")
        else:
            summary_lines.append(f"      - {name}: {v}")
    return summary_lines

def analyze_gwt_ops(ops, title):
    """Parses and logs individual GWT operations found inside resolved/unresolved blocks."""
    if not ops:
        return
    
    print(f"\n--- GWT Operations ({title}) ---")
    visual_elements_count = 0
    text_insertions_count = 0
    other_ops_count = 0
    
    for idx, op in enumerate(ops):
        if not isinstance(op, list) or len(op) == 0:
            continue
            
        op_code = op[0]
        
        if op_code == 3:
            # Shape / Visual Element Creation
            visual_elements_count += 1
            obj_id = op[1] if len(op) > 1 else "Unknown"
            shape_id = op[2] if len(op) > 2 else -1
            shape_name = SHAPE_TYPE_MAP.get(shape_id, f"SHAPE_TYPE_{shape_id}")
            
            print(f"  * Visual Element {visual_elements_count}:")
            print(f"    - ID: \"{obj_id}\"")
            print(f"    - Type: {shape_name} (ID: {shape_id})")
            
            # Transform matrix [scaleX, skewX, skewY, scaleY, tx, ty]
            if len(op) > 3 and isinstance(op[3], list) and len(op[3]) >= 6:
                t = op[3]
                # In GWT centipoint punch model, default width/height is 10000 centipoints (100 PT)
                scale_x, scale_y = t[0], t[3]
                tx, ty = t[4], t[5]
                
                w_pt = scale_x * 100
                h_pt = scale_y * 100
                x_pt = tx / 100
                y_pt = ty / 100
                
                print(f"    - Bounding Box:")
                print(f"      - Position: x = {x_pt:.2f} pt, y = {y_pt:.2f} pt ({tx} x {ty} centipoints)")
                print(f"      - Dimensions: w = {w_pt:.2f} pt, h = {h_pt:.2f} pt (scaleX={scale_x}, scaleY={scale_y})")
                
            # Styles list
            if len(op) > 4 and isinstance(op[4], list):
                styles = parse_styling_list(op[4])
                if styles:
                    print(f"    - Styles Applied:")
                    for line in format_style_summary(styles):
                        print(line)
                        
            # Parent
            if len(op) > 5:
                print(f"    - Parent Reference: \"{op[5]}\"")
                
        elif op_code == 15:
            # Text Insertion
            text_insertions_count += 1
            target_shape_id = op[1] if len(op) > 1 else "Unknown"
            text_val = op[4] if len(op) > 4 else ""
            print(f"  * Text Insertion {text_insertions_count}:")
            print(f"    - Destination Shape ID: \"{target_shape_id}\"")
            print(f"    - Text Content: \"{text_val}\"")
            
        else:
            other_ops_count += 1
            
    print(f"\n  Summary of '{title}' ops: {visual_elements_count} visual shapes, {text_insertions_count} text operations, {other_ops_count} others.")

def main():
    print("=========================================================")
    print("        GOOGLE SLIDES CLIPBOARD HIGH-FIDELITY ANALYZER    ")
    print("=========================================================")
    
    if not user32.OpenClipboard(None):
        print("[!] Error: Could not open the Windows Clipboard.")
        return
        
    try:
        # Enumerate all active formats for diagnostic purposes
        print("Active System Clipboard Formats found:")
        fmt = 0
        has_custom_mime = False
        while True:
            fmt = user32.EnumClipboardFormats(fmt)
            if fmt == 0:
                break
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClipboardFormatNameW(fmt, buf, 256)
            name = buf.value or f"Standard Format ID: {fmt}"
            print(f"  - Format ID {fmt:5d}: {name}")
            if name == CF_CHROMIUM_CUSTOM_NAME:
                has_custom_mime = True
                
        if not has_custom_mime:
            print("\n[!] Chromium Web Custom MIME format is NOT currently in the clipboard.")
            print("    Please copy some shapes from Google Slides first, then rerun this script.")
            return

        # Fetch custom Chromium Web Custom MIME format data
        h_data = user32.GetClipboardData(CF_CHROMIUM_CUSTOM)
        if not h_data:
            print("\n[!] Error: Could not retrieve data for Chromium Custom Clipboard Format.")
            return
            
        p_data = kernel32.GlobalLock(h_data)
        sz = kernel32.GlobalSize(h_data)
        if not p_data:
            print("\n[!] Error: Could not lock clipboard global memory handle.")
            return
            
        pairs = []
        try:
            raw_bytes = ctypes.string_at(p_data, sz)
            print(f"\n[+] Successfully locked and read {sz} raw bytes of custom MIME clipboard data.")
            pairs = decode_chromium_web_custom(raw_bytes)
        finally:
            kernel32.GlobalUnlock(h_data)
            
    finally:
        user32.CloseClipboard()
        
    print(f"[+] Decoded {len(pairs)} key-value MIME format pairs:")
    custom_dict = {}
    for k, v in pairs:
        print(f"  - MIME Type: \"{k}\" (value length: {len(v)} characters)")
        custom_dict[k] = v
        
    # Isolate drawings-object wrapped payload
    TARGET_MIME = "application/x-vnd.google-docs-drawings-object+wrapped"
    if TARGET_MIME not in custom_dict:
        print(f"\n[!] The target MIME type '{TARGET_MIME}' was not found in the custom pairs.")
        print("    Google Slides shapes might not be copied. Ensure you have copied individual canvas elements.")
        return
        
    wrapped_str = custom_dict[TARGET_MIME]
    try:
        outer_payload = json.loads(wrapped_str)
    except Exception as e:
        print(f"\n[!] Error parsing outer wrapper JSON from '{TARGET_MIME}': {e}")
        return
        
    print("\n--- Outer Envelope Payload Metadata ---")
    print(f"  - dih (Document ID Hash): {outer_payload.get('dih')}")
    print(f"  - edi (Editor Transaction / Session ID): {outer_payload.get('edi')}")
    print(f"  - edrk (Encryption / Session Reference Key): {outer_payload.get('edrk')}")
    print(f"  - dct (Data Content Type): {outer_payload.get('dct')}")
    print(f"  - cses (Client Side Encryption State): {outer_payload.get('cses')}")
    print(f"  - sm (Source Marker): {outer_payload.get('sm')}")
    
    inner_payload_str = outer_payload.get("data")
    if not inner_payload_str:
        print("\n[!] Error: No 'data' key found inside outer envelope payload.")
        return
        
    try:
        inner_payload = json.loads(inner_payload_str)
    except Exception as e:
        print(f"\n[!] Error decoding inner stringified GWT JSON payload: {e}")
        return
        
    # Write the beautifully formatted inner payload to copied_structure.json
    output_path = os.path.join("clipboard_iterations", "copied_structure.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(inner_payload, f, indent=2)
        print(f"\n[+] Beautifully formatted inner JSON successfully written to:")
        print(f"    '{output_path}'")
    except Exception as e:
        print(f"\n[!] Warning: Failed to save inner JSON structure to file: {e}")
        
    # Analyze resolved and unresolved operations inside the punch payload
    resolved_ops = inner_payload.get("resolved", [])
    unresolved_ops = inner_payload.get("unresolved", [])
    
    analyze_gwt_ops(resolved_ops, "resolved")
    analyze_gwt_ops(unresolved_ops, "unresolved")
    
    print("\n=========================================================")
    print("                     ANALYSIS COMPLETE                   ")
    print("=========================================================")

if __name__ == "__main__":
    main()
