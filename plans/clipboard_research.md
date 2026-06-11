# The Mechanics of Web Clipboard APIs and Google Slides Custom GWT Payload Formatting

## Executive Summary

* **Multimodal Clipboard Representations:** Operating systems and web browsers manage copied data through multiple concurrent representations (known as MIME types), allowing target applications to negotiate and select the most compatible format during a paste operation.
* **Proprietary Data Ecosystems:** Google Workspace applications (such as Docs, Slides, and Drawings) bypass standard HTML formatting by utilizing proprietary, JSON-based MIME types (specifically `application/x-vnd.google-docs-drawings-object+wrapped` for shapes and page elements) to preserve complex structural, positional, and styling data.
* **Format Negotiation Discrepancies:** The phenomenon where copied graphical objects fail to paste into plain text documents is an expected outcome of clipboard negotiation; the receiving application requests a plain text fallback representation, which often lacks the textual data embedded within the graphical vector models.
* **Programmatic Interoperability via Win32 ctypes:** Third-party desktop integrations can synthesize and inject raw Chromium custom clipboard payloads using Python and standard Windows APIs, bypassing web sandbox barriers to achieve seamless "copy to slide" vector placements.

---

## 1. Deconstructing the Proprietary Google Slides MIME Types

Google Workspace relies on two distinct clipboard formats depending on what content is being copied:

1. **`application/x-vnd.google-docs-drawings-page+wrapped`**: Used exclusively for copying ENTIRE slides or pages. When pasted, Google Slides handles this by creating a new slide card in the left navigator sidebar (and only works if the left navigator sidebar has focus).
2. **`application/x-vnd.google-docs-drawings-object+wrapped`**: Used for copying and pasting INDIVIDUAL shapes or groups of elements directly onto the active slide canvas. **This is the exact MIME type needed for shape-to-slide paste operations.**

### The Envelope Schema
The top-level envelope features a `"dih"` session/document hash and a double-serialized `"data"` payload:
```json
{
  "dih": 1245482604,
  "data": "{\"resolved\": [...], \"unresolved\": [...], \"autotext_content\": {}, ...}",
  "dct": "punch",
  "ds": false,
  "cses": false,
  "sm": "other"
}
```

---

## 2. Reverse-Engineered GWT "Punch" Drawing Format

Through high-fidelity diagnostic testing and decoding of the native Windows clipboard, we have reverse-engineered the GWT **"punch"** drawing format.

### 2.1 The Coordinate Scaling System
The "punch" format does not use points or EMUs directly. It utilizes **Centipoints** (1/100th of a standard Point, or `EMU / 127`):
* `1 PT = 100 Centipoints`
* `1 Inch = 7200 Centipoints`

The base scaling depends heavily on the element's shape type:
* **Standard Visual Shapes (e.g. RECTANGLE, ELLIPSE)**: Have a default internal bounding box width/height of `10,000 centipoints` (100 PT).
  * `width_in_points = scaleX * 100`
  * `height_in_points = scaleY * 100`
  * `position_x_in_points = tx / 100`
  * `position_y_in_points = ty / 100`
* **Paths and Lines (SHAPE_TYPE_153)**: Have a default internal length of `120,000 centipoints` (1,200 PT).
  * `line_length_in_points = scaleX * 1200`
  * `stroke_height_in_points = scaleY * 1200`

### 2.2 Visual Element Creation (Op Code 3)
Operations inside `"resolved"` and `"unresolved"` lists are flat arrays representing canvas transformations:
```json
[
  3,
  "objectId",
  shapeTypeId,
  [scaleX, skewX, skewY, scaleY, tx, ty],
  [style_key, style_val, style_key, style_val, ...],
  "p"
]
```
Where:
* `3` is the operation code for creating a visual shape element.
* `shapeTypeId` determines the visual primitive:
  * `4` = `ELLIPSE` (Circle)
  * `6` = `RECTANGLE`
  * `108` = `TEXT_BOX`
  * `153` = `LINE_PATH` (Curves, lines, borders, and ticks)
* `"p"` represents the parent reference tag.

### 2.3 Corrected Styling Key Maps
Prior analyses falsely assumed that key `14` was a generic prefix. In reality, GWT punch uses key-value styling tuples where:
* **Key `14` (Fill Active State):** A boolean active indicator.
  * `1` = Solid background fill color (renders the hex color assigned to key `15`).
  * `0` = Transparent background / NOT_RENDERED (renders shape outline only, ignoring color styling).
* **Key `15` (Fill Background Color):** Hex background fill color string (e.g., `"#cfe2f3"`).
* **Key `16` (Stroke Solidity Flag):** Active state of the outline border (`1` = active, `0` = inactive).
* **Key `18` (Stroke Option Flag):** Option flag governing outline rendering (`1` = active).
* **Key `19` (Stroke Outline Color):** Hex outline border color string (e.g., `"#0b5394"`).
* **Key `22` (Stroke Weight):** Outline stroke thickness in centipoints (`width_in_points * 100`, e.g., `200` = 2 pt).
* **Key `27` (Start Arrowhead Size/Style):** Renders custom start arrowhead size/scale modifier (default `1.3`).
* **Key `30` (End Arrowhead Size/Style):** Renders custom end arrowhead size/scale modifier (default `1.3`).
* **Key `43` (Dash Style State):** Determines line segments rendering:
  * `0` = Solid continuous border line.
  * `2` = Dashed / dotted intermediate segment gridline.
* **Key `44` (Text Vertical Alignment/Active Flag):** Determines vertical styling active state (default `0`).
* **Key `45` (Text Container Alignment Style):** Governs vertical alignment and bounds padding for text container (usually `1`).
* **Key `60` (Margin padding state):** Standard spacing value flag (usually `0`).

### 2.4 Logical Element Grouping (Op Code 2)
To combine individual visual objects on the canvas into a single cohesive, selectable element (such as grouping hundreds of tiny curve segments), GWT utilizes Operation Code `2`:
```json
[
  2,
  "groupId",
  ["childId_1", "childId_2", "childId_3", ...],
  [scaleX, skewX, skewY, scaleY, tx, ty],
  "parentId"
]
```
Where:
* `2` is the GWT operation code for logical grouping.
* `"groupId"` is the unique identifier for the group shape.
* The third element is a list of child shape/line/text IDs being logically grouped.
* The fourth element is a transformation matrix specifying the group's transform scale/offset.
* `"parentId"` is the parent canvas or slide page containing the group.

This is critical because Programmatic curves in GWT are represented as sequences of hundreds of individual line segments (Shape Type `153`). Without logical grouping operations, pasting a curve would litter the slide canvas with unselectable standalone line segments. Grouping packages them seamlessly!

---

## 3. High-Fidelity Text Box Insertion (Op Codes 15 & 17)

To create a fully functional, editable text label inside Google Slides, GWT requires a synchronized multi-operation sequence:

1. **Shape Creation (Op Code 3):**
   Creates a container text box using `shapeTypeId = 108` with a transparent background style `[44, 0]`.
2. **Text Character Injection (Op Code 15):**
   `[15, "shapeId", null, 0, "text_content"]` (places the raw string characters inside the target shape ID).
3. **Alignment & Formatting Configs (Op Code 17):**
   * Alignment (e.g. Center): `[17, "shapeId", None, 3, 4, [], [12, 2]]` where `[12, 2]` represents center paragraph formatting.
   * Typography: `[17, "shapeId", None, 0, 4, [], [5, "Ubuntu", 6, 16]]` where `5` is the font family name, and `6` is the font size in points (`16 pt`).
4. **Envelope Mappings (`autotext_content`):**
   Every text box shapeId must be registered in the outer envelope's `autotext_content` map as `"{\"shapeId\":\"<textbox_id>\"}": {}` to prevent the browser from stripping paragraph overrides upon pasting.

---

## 4. Programmatic Clipboard Spoofing on Windows 11 (PowerShell & Python)

To programmatically write Google-compatible visual elements to the Windows clipboard, scripts must write directly to the OS pasteboard under the registered layout of `"Chromium Web Custom MIME Data Format"`.

### Working Python Binary Encoder
The following Python implementation registers the Chromium clipboard handle, structures multiple mime-type pairs (GWT wrapped json + tracking ID), and locks standard movable global memory blocks to ensure high-fidelity Windows copy-paste injection:

```python
import ctypes
import json

# Bind to Win32 dynamic libraries
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Cast parameters to maintain x64 address safety
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
    """
    Encodes multiple MIME pairs into Windows clipboard buffer stream:
    [4 bytes total pairs length] + [4 bytes pair count] + pairs data...
    """
    data = b""
    for k, v in pairs:
        # Key string: prefixed by uint32 character length, encoded in UTF-16LE, padded if length is odd
        data += len(k).to_bytes(4, "little") + k.encode("utf-16le")
        if len(k) % 2 != 0:
            data += b"\0\0"
        # Value string: prefixed by uint32 character length, encoded in UTF-16LE, padded if length is odd
        data += len(v).to_bytes(4, "little") + v.encode("utf-16le")
        if len(v) % 2 != 0:
            data += b"\0\0"
    total_data = len(pairs).to_bytes(4, "little") + data
    return len(total_data).to_bytes(4, "little") + total_data

def set_clipboard_data(pairs, text_fallback=""):
    """Injects GWT pairs and text fallbacks directly into Windows Clipboard."""
    raw_custom_bytes = encode_chromium_web_custom(pairs)
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        
        # 1. Custom Chromium MIME Format
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw_custom_bytes))
        if h_mem:
            p_mem = kernel32.GlobalLock(h_mem)
            if p_mem:
                ctypes.memmove(p_mem, raw_custom_bytes, len(raw_custom_bytes))
                kernel32.GlobalUnlock(h_mem)
                user32.SetClipboardData(CF_CHROMIUM_CUSTOM, h_mem)
                
        # 2. Plain Text Fallback
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
```

---

## 5. Working High-Fidelity Binary Clipboard Decoder

To inspect the system clipboard and parse GWT drawing payloads copied directly from Google Slides, the following Python script successfully opens the pasteboard, unpacks the UTF-16LE binary sequence, decodes the outer wrapped envelope, extracts the inner GWT operations, and logs a comprehensive overview of visual shapes, line scaling, text alignments, and styling parameters:

```python
import ctypes
import json

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
    padding = 2 if length % 2 != 0 else 0
    total_len = 4 + byte_length + padding
    if len(bs) < 4 + byte_length:
        return "", b""
    text = bs[4 : 4 + byte_length].decode("utf-16le", errors="replace")
    return text, bs[total_len:]

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
        print("Failed to open clipboard.")
        return

    try:
        h_data = user32.GetClipboardData(CF_CHROMIUM_CUSTOM)
        if h_data:
            p_data = kernel32.GlobalLock(h_data)
            sz = kernel32.GlobalSize(h_data)
            if p_data:
                try:
                    raw_bytes = ctypes.string_at(p_data, sz)
                    pairs = decode_chromium_web_custom(raw_bytes)
                    
                    for k, v in pairs:
                        if k == "application/x-vnd.google-docs-drawings-object+wrapped":
                            outer = json.loads(v)
                            inner = json.loads(outer["data"])
                            print(f"Decoded {len(inner.get('resolved', []))} total GWT operations!")
                            print(json.dumps(inner, indent=2)[:2000] + "...")
                finally:
                    kernel32.GlobalUnlock(h_data)
    finally:
        user32.CloseClipboard()

if __name__ == "__main__":
    main()
```

---

## 6. Case Study: Programmatic Multi-Panel Vector Plots (Kinematics Grid)

Through programmatic extraction and incremental rebuilding, we successfully analyzed and reproduced the **"Overzicht van Bewegingstypen (Grid)"** diagram—a high-fidelity 3x2 grid of kinematics sub-graphs.

### 6.1 Layout & Component Clustering
The diagram consists of several layers of vector primitives organized into precise grid-aligned coordinate bands:
1. **Title & Layout Frames:**
   * A central document title: `"Overzicht van Bewegingstypen (Grid)"` is rendered in **Ubuntu 20pt Bold** (`#0B5394` blue).
   * **6 Bounding Rectangles** (Shape ID `6`) with transparent fill and solid black outlines act as the boundaries of the sub-graphs.
2. **Dashed Gridlines:**
   * Each sub-graph features internal vertical and horizontal dashed gridlines (Shape ID `153`) colored with a light grey hex outline (`#EEEEEE`) and dashed/dotted style key `43` set to `2`.
3. **Axis Ticks and Variable Labels:**
   * Standardized labels `"0"`, `"1"`, `"2"`, `"3"`, `"4"`, `"5"` (Shape ID `108` textboxes) are grouped around the margins of each bounding panel.
   * Coordinate variables `"t"`, `"x"`, and `"v"` are perfectly aligned at the ends of axes to describe the physical dimensions.
4. **Segmented Functional Curves:**
   * Since GWT lacks an explicit algebraic function plotting primitive, continuous plots are discretized and drawn using sequences of hundreds of individual straight segment lines (Shape ID `153`).
   * Curves are split into distinct functional series:
     * **Green series (`#38761D`):** Stationary kinematics plots ($x(t)$ horizontal, $v(t)$ at zero).
     * **Blue series (`#0B5394`):** Constant velocity kinematics plots ($x(t)$ linear slope, $v(t)$ horizontal non-zero).
     * **Red series (`#980000`):** Constant acceleration kinematics plots ($x(t)$ parabolic curve, $v(t)$ linear slope).
### 6.2 Key Structural Findings for Large Vector Diagrams
* **Group Management (Op Code 2):** Large-scale drawings containing thousands of elements rely on `Op Code 2` grouping. This groups curve segments into selectable components, preventing canvas clutter and enabling group translation and scaling operations without breaking function continuity.
* **Autotext Registrations:** Every text box and custom label must have a parallel mapping inside the outer envelope's `autotext_content` table. Omitting this causes Google Slides' clipboard negotiator to strip formatting, sizes, and fonts upon paste.
* **MIME Envelope Preservation:** Complex coordinates and multiple MIME formats (e.g. `application/x-vnd.google-docs-drawings-object+wrapped` and plain text fallbacks) must be packaged cleanly using Windows global movable memory structures to ensure a reliable paste operation.

---

## 7. LaTeX/SVG Formula Representation (Test: Lorenz Attractor)

**Date:** 2026-06-10
**Experiment:** `clipboard_iterations/test_latex_view/`
**Source Graph:** Lorenz Attractor (X-Z plane projection) with 3 embedded LaTeX equations

### 7.1 Critical Discovery: No Vector Path Representation
LaTeX equations in Google Slides are **NOT** represented as custom vector paths (Shape Type 153) or editable text. Instead:

* **Shape Type:** `3` (SHAPE_TYPE_3) — typically reserved for images/pictures
* **Scale Factors:** Extremely large (e.g., `296.7308 × 296.7498`) indicating the internal SVG coordinate space is mapped to a tiny visual bounding box
* **Style Key 39:** Contains a Google Drive URL pointing to the rendered SVG:
  - `https://drive.google.com/uc?id=1d4wQ-xMRo-hgWEt_fj50GFAuXvQ_Q-Ps&export=download`
  - `https://drive.google.com/uc?id=1LLC4xJtr7xulr3Kjic0to2KA-kpVpzO7&export=download`
  - `https://drive.google.com/uc?id=1_5mQAYLlB3HHApK5nMinFqOMBIDd6chc&export=download`
* **Style Key 49:** Contains blob identifier (`s-blob-v1-IMAGE-fFuVjqVvxLQ`)
* **Style Keys 8 & 9:** Dimension metadata (e.g., `260, 54`)

### 7.2 Background Rectangles
Each LaTeX formula is paired with a white background rectangle:
* **Shape Type:** `6` (RECTANGLE)
* **Fill:** `#FFFFFF` (solid white)
* **Purpose:** Provides contrast behind the transparent SVG formula

### 7.3 Title Text Box
* **Shape Type:** `108` (TEXT_BOX)
* **Text Insertion:** Requires synchronized operations:
  - Op `3`: Creates the shape container with transform `[1.6933, 0, 0, 0.1905, 81280, 3810]`
  - Op `15`: Inserts raw text string `"Lorenz Attractor (X-Z plane projection)"`
  - Op `17` (×2): Applies formatting (color `#0B5394`, font `Ubuntu`, size `18`)
* **Critical Bug Found:** Omitting Op `15` creates an empty text field (user sees placeholder but no content)

### 7.4 Implications for Reconstruction
* LaTeX formulas **cannot** be procedurally generated via vector paths
* External SVG hosting (Google Drive) is required for formula fidelity
* Future work must either:
  1. Pre-render LaTeX to SVG and upload to Drive, or
  2. Accept that LaTeX elements are opaque image blobs in the GWT format
### 7.5 Questions for Future Iterations
1. Can we intercept/replace the Google Drive URLs with our own hosted SVGs?
2. What is the internal coordinate system of the SVG blobs (Style Keys 8/9)?
3. Can we create new LaTeX formulas by uploading new SVGs and constructing matching SHAPE_TYPE_3 entries?

### 7.6 Critical Z-Order Finding & Google Drive Crash (Step 4 & 5 Verification)
**Date:** 2026-06-10
**Issue 1: Google Drive Sync Crash ("Can't sync your changes")**
* **Symptom:** Programmatically constructed axis labels with incorrect format parameters caused Google Slides to trigger an unrecoverable sync crash: *"Can't sync your changes. Copy your recent edits, then revert your changes."*
* **Root Cause:** Programmatic mismatch of GWT Op Type `17` formatting list elements. While we originally modeled typography using lists like `[0, 1, 4, "#000000", 5, "Ubuntu", 6, 10]`, the Slides GWT system strictly requires the exact format matching the source slides document. For standard axis labels, the schema requires:
  - Alignment: `[17, shapeId, None, 3, 4, [], [12, 2]]` (instead of using `39` or `40`)
  - Typography: `[17, shapeId, None, 0, 4, [], [5, "Ubuntu", 6, 16]]`
* **Resolution:** Reverted all axis label formatting operations to strictly match the source GWT parameters. Once the parameters matched, the sync errors resolved immediately.

**Issue 2: Layer Visibility & Depth (Curves vs. Equations & Axes)**
* **Symptom:** Placing curve segments at the top of the array rendered the curves in front of the LaTeX equations and the black axes, reducing readability.
* **Resolution:** Re-architected the explicit z-order array serialization:
  1. **Layer 1 (Bottom):** Gridlines (`_g_grid_jpd6` group and its 11 lines)
  2. **Layer 2 (Middle-Bottom):** Complete Curve segments (all 996 `diffeq_segment_*` curve components)
  3. **Layer 3 (Middle-Top):** LaTeX formulas and background white rectangles (`_element_1021_text`, etc.)
  4. **Layer 4 (Top-Axes):** Main axes lines and arrowheads (`_axes_group`)
  5. **Layer 5 (Top-Labels):** Axis label textboxes and number labels
  6. **Layer 6 (Top-Most):** Main slide title
* **Implication:** Element placement order in GWT resolved/unresolved arrays dictates literal z-order rendering. Formulas, axes, and text overlays must appear *after* curves and grids in the serialization array.

---

## 8. Connector Line GWT Validation & Mathematical Coordinate Scaling

Through systematic binary-search style diagnosis of GWT style keys and coordinate analysis matching successful Python payloads, we resolved the two most critical issues for browser-to-slides vector copying: connector line validation failures and absolute scaling discrepancies.

### 8.1 GWT Validation Rules for Straight Connectors (Shape Type 153)
* **The "none" Fill Restriction:** Google Slides' GWT validation engine strictly validates straight connector lines (Shape Type `153`). It **completely rejects payloads containing `"none"` for Style Key `15` (Fill color)**, even when fill rendering is explicitly disabled via key-value pair `14, 0`. Standard visual shapes like Rectangles (`6`) and Ellipses (`8`) accept `"none"` perfectly, but connectors do not.
* **The Hex Color Fallback Solution:** To prevent Google Slides from silently dropping pasted elements containing lines, we must assign a solid hex color string (e.g. `"#EEEEEE"` or `"#000000"`) to Key `15` for all connector lines. Since fill rendering is disabled (`14, 0`), Google Slides ignores this color visually, but GWT schema validation succeeds, allowing the line to paste perfectly.
* **Arrowhead Keys:** Keys `27` (Start size), `30` (End size), `28` (Start style), and `29` (End style) are optional and not required for a line paste to succeed, but end arrowhead value `5` (Stealth arrowhead) works flawlessly for directional connectors.

### 8.2 Standard GWT Coordinate Translation and Scaling
* **The 127 Scale Factor:** GWT translation coordinates (`translateX` / `translateY` or `tx` / `ty` at index 4 and 5 of the transform matrix) and standard shape dimensions (`w_cp` / `h_cp`) are internally represented in **EMUs (English Metric Units) divided by 100**.
  - Since `1 Point = 12,700 EMUs`, the conversion is exactly:
    $$\text{GWT units} = \text{Points} \times 127$$
  - Previous assumptions of `100` or `1000` resulted in elements pasting at `1.27x` smaller than actual size (squeezed to top-left) or `10x` larger than actual size (overflowing canvas boundaries). Scaling all coordinate transformations and dimensions by exactly `127` yields a perfect 1:1 match.
* **Stroke Weight Scaling:** Stroke weights (such as Style Key `22`) are scaled in GWT units as well:
  $$\text{Stroke GWT units} = \text{Stroke Width (PT)} \times 1270$$
  - A stroke width of `0.4 PT` translates to exactly `508` GWT units.
  - A stroke width of `1.2 PT` translates to exactly `1524` GWT units.

### 8.3 Base Transform Scaling for Shape Type 153 (Connector)
* Unlike Standard Shapes (`6`, `8`, `108`) which are modeled around a default bounding box of `10,000` GWT units (making `scaleX = w_cp / 10000`), Connector lines have an internal GWT base size of `120 PT` (`12,000` GWT units / centipoints).
* Therefore, the scaling factors for a connector line from coordinate $(x_1, y_1)$ to $(x_2, y_2)$ are calculated as:
  $$\text{scaleX} = \frac{\Delta x}{120}$$
  $$\text{scaleY} = \frac{\Delta y}{120}$$
  And translation is positioned at the start coordinate:
  $$tx = x_1 \times 127$$
  $$ty = y_1 \times 127$$

