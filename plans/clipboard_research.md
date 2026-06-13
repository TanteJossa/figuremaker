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

---

## 9. Frontend-to-Backend Clipboard Pipeline Review (2026-06-13)

A code review of the current production pipeline (`templates/index.html` + `app.py`) identified several discrepancies between the documented GWT rules and the generated payloads. These discrepancies are the prime suspects for why only the **Sinusoidal** and **Lorenz Attractor** presets paste successfully while **Area**, **Phases**, **Parametric**, and **Multi-Grid** presets fail.

### 9.1 Suspect 1: Z-Index Sorting Breaks Group Child Ordering

`app.py::convert_to_google_slides_json()` sorts every slide element by an inferred z-index before serializing GWT operations. Groups are sorted as ordinary elements. In GWT, a group operation (`opcode 2`) must appear **after** all of its child shape operations, because it references them by ID. The current sorter does not keep children and their group together:

* Axes lines/arrows are detected as `Layer 3` (axis), but the `axes_group` wrapper falls back to `Layer 1`.
* Grid lines are `Layer 0`, but their grid group is `Layer 1`.
* For Lorenz the curve segments and the `diffeq_trajectory_group` both default to `Layer 1`, so stable sorting preserves children-before-group and the paste works.
* For Sinusoidal the `axes_group` is the only group and it may be silently ignored by Slides, letting the individual lines still render.

**Hypothesis:** Complex graphs with multiple groups fail because at least one group is serialized before its children, causing GWT validation/paste rejection.

### 9.2 Suspect 2: Coordinate Scale Uses 508 Instead of 127

Section 8.2 established that GWT units are `Points × 127`. However, `app.py` currently multiplies all positions and dimensions by `508` (which is `127 × 4`). Because every element in a graph uses the same wrong scale, relative layout is preserved, which explains why simple graphs still look correct. But the absolute coordinates are 4× too large and may trigger Slides validation/size limits on graphs with many elements or extreme positions.

Related observations:
* Connector scale in `app.py` is `(dx × 508) / 120000`, which simplifies to `dx / 236.22`. The research-derived value should be `dx / 120` when `dx` is in points, or equivalently `(dx × 127) / 120000`.
* Stroke weights are also scaled by `508` instead of `1270`.

**Hypothesis:** The 4× scale factor is tolerated for small payloads but may cause large/complex payloads to be rejected.

### 9.3 Suspect 3: Text Box Base Scale Uses 100000 Instead of 10000

`app.py` creates text box shapes (`shapeTypeId = 108`) with `scaleX = w_cp / 100000` and `scaleY = h_cp / 100000`. Per section 8.3, text boxes are standard visual shapes and should use the `10000` GWT-unit base. This makes the text container 10× smaller than intended. Again, the actual text may still render, but selection handles and bounding-box validation can be wrong.

### 9.4 Suspect 4: Missing or Unstable Element IDs

Several frontend drawing routines push elements without explicit `id` fields:
* Hatch vertical lines
* Phase marker lines/rects/texts
* Grid lines in single-viewport mode

`app.py` then generates IDs such as `element_{index}_{el_type}`. Because the index depends on the sorted order, a child ID can change relative to its group reference, breaking groups after sorting.

### 9.5 Suspect 5: Frontend Binding Bug on Custom Lines

In `templates/index.html` line 687, the Y2 input for custom lines is bound to `v-model.number="ln.x2"` instead of `ln.y2`. While the preset values initialize Y2 correctly, any user edit corrupts the data. This is not the root cause of preset failures but should be fixed.

### 9.6 Suspect 6: Missing Width/Height on Text Labels

Many text labels (especially screen-space titles and axis names) do not provide `width`/`height`. `app.py` falls back to `400 × 37.5` points, which may produce oversized or misaligned text boxes that interfere with paste validation.

---

## 10. Iterative Diagnostic Protocol

To confirm which hypothesis is the actual failure mode, we will capture the live Windows clipboard after copying from the site and after copying a correct native Slides model.

### Step A — Capture a failing site copy
1. Start the Flask app (`python app.py`) and open `http://127.0.0.1:5000`.
2. Select a **failing** preset, e.g. **Area Between Curves** or **Multi-Grid Layout**.
3. Click **Copy to Google Slides**.
4. Run `python extract_last_copy.py` (or `python clipboard_iterations/analyze_clipboard.py`) to save the clipboard to `last_clipboard.json`.
5. Rename the output to `last_clipboard_failed.json`.

### Step B — Capture a correct native Slides model
1. In Google Slides, draw or paste a correct version of the same diagram type (or a simple grouped shape).
2. Select the shapes and press **Ctrl+C**.
3. Run `python extract_last_copy.py` to save to `last_clipboard.json`.
4. Rename the output to `last_clipboard_reference.json`.

### Step C — Compare
1. Run `python compare_sine_wave_clipboards.py` or a custom diff script against the two captures.
2. Inspect:
  * Whether groups appear before their children in the failed capture.
  * Whether the absolute coordinate ranges are ~4× larger than the reference.
  * Whether text boxes use `shapeTypeId 108` with plausible scale factors.
  * Whether any operation IDs are referenced but missing.

### Step D — Fix and validate
1. Apply the smallest fix that matches the reference structure.
2. Repeat Step A with the same failing preset.
3. Paste into Google Slides and confirm success.

---

## 11. Preliminary Fix Roadmap

Based on the code review, the likely fixes are:

1. **Group-aware serialization:** Do not sort groups independently. Either (a) disable z-index sorting and rely on the frontend's already-correct push order, or (b) keep groups with their children by assigning the group's z-index to all children and emitting the group op immediately after the last child.
2. **Correct the GWT scale factor from 508 to 127** for positions, dimensions, and connector base scaling; use `1270` for stroke weights.
3. **Correct text box base scale from 100000 to 10000**.
4. **Assign stable explicit IDs** to every hatch line, phase marker sub-element, and grid line so that group references remain valid after sorting.
5. **Fix the Y2 binding bug** in `templates/index.html`.
6. **Provide explicit width/height** for all text labels or compute them from font metrics.

> **Important:** We will validate each hypothesis with real clipboard captures before applying fixes, to avoid changing multiple variables at once.

---

## 12. Multi-Grid Clipboard Capture — Findings (2026-06-13)

We captured the clipboard after selecting the **Multi-Grid Layout** preset and clicking **Copy to Google Slides**. The payload was saved as `last_clipboard_failed.json` and compared against the previously captured native reference `clipboard_iterations/test_grid_view/copied_structure.json`.

### 12.1 Validation Results

Running `validate_failed_payload.py` on the failed Multi-Grid copy showed:

* **No duplicate SHAPE CREATION IDs** (text ops legitimately reuse text-box IDs).
* **All 12 groups have children defined before the group operation** (opcode 2 ordering is valid).
* **All text shapes are registered in `autotext_content`**.
* **No `NaN` or `Infinity` values** in the serialized JSON.

These results rule out the initial suspects of duplicate IDs, broken group ordering, missing autotext, and numerical corruption.

### 12.2 Comparison Against Native Grid Reference

| Metric | Failed Site Copy | Native Reference | Difference |
|--------|------------------|------------------|------------|
| Total resolved ops | 1330 | 1330 | Identical |
| Rectangles (shape 6) | 6 | 6 | Identical |
| Text boxes (shape 108) | 91 | 91 | Identical |
| Line paths (shape 153) | 948 | 948 | Identical |
| Text insertions (op 15) | 91 | 91 | Identical |
| Format ops (op 17) | 182 | 188 | **−6** |
| **Group ops (op 2)** | **12** | **6** | **+6** |
| Autotext keys | 91 | 97 | **−6** |
| Scale X range | 0.0001 – 8.636 | 0.0004 – 1.6933 | Different |
| X coordinate range | 5080 – 349504 | −177800 – 349504 | Reference has negative X |

### 12.3 Key Finding: Grid Lines Are Grouped, Reference Curves Only

The failed site copy creates **12 groups**: one grid-line group and one curve group for each of the 6 cells. The native reference contains only **6 groups**, and inspection of the reference group IDs (`g_mg_c_*`) shows that it groups **only the curve segments**, not the grid lines.

The Multi-Grid frontend code at `templates/index.html` (around lines 1720-1735 and 1883-1897) wraps every cell's dashed grid lines into a group. The native Google Slides copy of the equivalent diagram does not do this.

### 12.4 Diagnosis (Updated After Fresh Native Capture)

The fresh native Multi-Grid capture also contains **12 groups**, so grid-line grouping is **not** the cause. The real difference is in the **6 cell-frame rectangles**:

| Rectangle Property | Failed Site Copy | Native Reference |
|--------------------|------------------|------------------|
| Fill color (key 15) | `"none"` | `"#EEEEEE"` |
| Stroke option flag (key 18) | **missing** | `1` |
| Dash style (key 43) | **missing** | `0` |
| Margin padding flag (key 60) | **missing** | `0` |
| Format op (opcode 17) | **missing** | `[17, rect_id, None, 0, 1, [], [12, 2]]` |
| Autotext registration | **missing** | registered in `autotext_content` |
| Scale factors | `8.636 × 6.096` | `0.7197 × 0.508` |

The native reference applies a format op and autotext registration to every rectangle, even though the rectangles contain no text. The working Sine Wave reference does the same for its white background rectangles behind LaTeX labels.

**Revised diagnosis:** The Multi-Grid paste fails because the 6 cell-frame rectangles are serialized as bare shapes without the format op and autotext registration that Google Slides' GWT validator expects. Additionally, the rectangle style uses `"none"` for fill and omits keys `18`, `43`, and `60`.

### 12.5 Proposed Fix for Multi-Grid

Update the rectangle serialization in `app.py` (and/or the rectangle element generation in `templates/index.html`) so that every rectangle:

1. Uses a solid hex fill color for key `15` (e.g. `"#EEEEEE"`) even when fill is disabled (`14, 0`).
2. Includes style keys `18, 1`, `43, 0`, and `60, 0`.
3. Receives a format op `[17, rect_id, None, 0, 1, [], [12, 2]]`.
4. Is registered in `autotext_content`.

This matches the native reference and the working Sine Wave background rectangles.

---

## 13. Post-Fix Backend Comparison (Multi-Grid)

After applying the rectangle fix (format op + autotext + style keys `18`, `43`, `60`) in `app.py`, a fresh backend-generated Multi-Grid payload was produced from [`test_graph_grid.json`](test_graph_grid.json) and compared against the native reference.

| Metric | Generated Payload | Native Reference | Difference |
|--------|-------------------|------------------|------------|
| Total resolved ops | 1630 | 1330 | **+300** |
| Rectangles (shape 6) | 6 | 6 | Identical |
| Text boxes (shape 108) | 91 | 91 | Identical |
| Line paths (shape 153) | **1248** | **948** | **+300** |
| Text insertions (op 15) | 91 | 91 | Identical |
| Format ops (op 17) | 188 | 188 | Identical |
| Group ops (op 2) | 6 | 6 | Identical |
| Autotext keys | 97 | 97 | Identical |
| Style keys present | 14, 15, 18, 19, 22, 27, 30, 43, 44, 60 | same | Identical |

The 300 extra line ops correspond to **50 additional curve segments per cell** in the source data (`test_graph_grid.json` uses 200 segments per curve; the reference uses 150). This is a data-density difference, not a structural error.

### 13.1 Remaining Differences vs. Native Reference

* **Line stroke weight scaling**: Generated `22` values are `stroke_width * 508`; reference line weights are half that (`254` for a 1 px line). Rectangle stroke weights in the reference still match the `* 508` factor, so the line-weight unit may be different or the reference graph simply had thinner lines.
* **Group contents**: Generated groups contain 200 curve-segment IDs each; reference groups contain 150. Both are valid group sizes.
* **Envelope `dih` / `edi` / `edrk`**: The generated wrapper still uses the hardcoded envelope from the working Sine Wave payload. The native reference has different `dih`, `edi`, and `edrk` values. It is unknown whether Google Slides validates these for larger payloads.
* **Missing `application/x-vnd.google-docs-document-slice-clip+wrapped`**: Native copies include this third MIME pair; the site only writes the drawings object and internal clip-id pairs. Sine Wave works without it, but it may become required for larger or grouped objects.

## 14. Next Step — Isolate Frontend vs. Backend Failure

Because the backend payload now matches the reference counts for format ops, autotext, groups, and style keys, the continued paste failure is likely caused by one of two things:

1. **Backend payload still invalid** (e.g., envelope hash, missing document-slice-clip, or an unobserved GWT structural rule).
2. **Frontend copy mechanism** (`document.execCommand('copy')` + `event.clipboardData.setData`) failing silently for the larger (~500 KB) Multi-Grid payload even though it returns `true`.

To isolate, run the following two tests:

1. **Bypass the frontend**: Run `python write_generated_grid_to_clipboard.py` in the project folder, then paste into Google Slides. If this works, the backend payload is valid and the site copy button needs to switch to `navigator.clipboard.write` (ClipboardItem/Blob) for large payloads.
2. **Verify the site actually writes the clipboard**: After clicking *Copy to Google Slides* on the site, run `python extract_last_copy.py` and check whether `last_clipboard.json` contains the `application/x-vnd.google-docs-drawings-object+wrapped` key. If it is missing or truncated, the frontend copy path is the problem.

Based on the result we will either fix the envelope/wrapper or replace the frontend copy implementation.

## 15. Isolation Result — Backend Payload Is Valid

The direct clipboard injection test (`python write_generated_grid_to_clipboard.py`) pasted successfully. This proves that the backend-generated GWT payload is valid; the remaining failure was caused by the frontend copy path failing to deliver the large (~500 KB) payload to the clipboard.

During the direct-paste test the grid cell frames were rendered as oversized rectangles. This identified a second bug in the old rectangle serialization: rectangles were scaled with a `10,000` centipoint denominator instead of the `120,000` denominator used by lines and ellipses.

## 16. Implemented Fixes

### 16.1 New `SlidesBuilder` class (`slides_builder.py`)

A dedicated builder module was added to centralize GWT serialization:

* `add_rect()` — uses the correct `120,000` centipoint denominator, always emits format op `17` and registers the rectangle in `autotext_content`, and supplies style keys `18, 43, 60`.
* `add_ellipse()` — uses the `120,000` denominator and native ellipse styling.
* `add_line()` — supports dashed lines, start/end arrowheads, and the `0.0004` zero-scale fallback used by native copies.
* `add_text()` — emits shape creation, text insertion (`op 15`), alignment format (`op 17`), typography format (`op 17`), and autotext registration.
* `add_group()` — emits group op `2` with the identity transform.
* `to_punch()` — returns both the flat inner JSON and the wrapped envelope expected by Google Slides.

`app.py` now imports `SlidesBuilder` and `convert_to_google_slides_json()` delegates element serialization to it, replacing the long inline serialization block.

### 16.2 Frontend copy switched to `navigator.clipboard.write`

`templates/index.html` `executeBrowserCopy()` now:

1. Tries `navigator.clipboard.write()` with a `ClipboardItem` containing Blobs for:
   * `application/x-vnd.google-docs-drawings-object+wrapped`
   * `application/x-vnd.google-docs-internal-clip-id`
   * `text/plain`
   * `text/html`
2. Falls back to the original `document.execCommand('copy')` path if the modern API is unavailable or throws.

`copyToGoogleSlides()` and `copyTestShape()` were updated to `await` the now-async `executeBrowserCopy()`.

## 17. Verification From the Site — Multi-Grid Works

After restarting the Flask server and hard-refreshing the browser:

* **Multi-Grid Layout** now copies from the site and pastes into Google Slides successfully.
* Grid cell rectangles render at normal size.

## 18. Remaining Presets to Verify

The builder-based fix is generic, so the same presets that previously failed should now work. Please test and report:

1. **Area Graph**
2. **Phases**
3. **Parametric**

If any of these still fail, capture the clipboard with `python extract_last_copy.py` and share the result.

## 19. LaTeX Equations Are a Different Clipboard Format

The user copied a native Google Slides equation. The resulting clipboard contains three MIME types, not just the drawings-object wrapper:

* `application/x-vnd.google-docs-document-slice-clip+wrapped` — contains an entity map pointing to an image blob (`eo_type: 0`, image src URL, dimensions).
* `application/x-vnd.google-docs-drawings-object+wrapped` — contains a single shape with `shapeTypeId = 3` (image placeholder), style keys `15, 177, 19, 22, 39, 49, 8, 9`, and the image URL.
* `application/x-vnd.google-docs-image-clip+wrapped` — maps the image blob ID to a filesystem/persistent URL.

This means Google Slides stores equations as **image blobs**, not as text shapes. Supporting LaTeX paste would require:

1. Rendering each LaTeX label to an image (SVG/PNG) on the frontend or backend.
2. Uploading that image to a URL accessible to Google Slides (e.g., Google Drive).
3. Generating the additional `document-slice-clip+wrapped` and `image-clip+wrapped` MIME entries.

That is a separate feature, not a bug in the graph shape serialization. The current shape-based `SlidesBuilder` is not designed for image blobs.

## 20. LaTeX Image Support Implementation

Implemented LaTeX equation image support for clipboard paste.

### 20.1 Backend: `graph_engine.compile_latex_to_svg`

A new function [`compile_latex_to_svg()`](graph_engine.py:1098) renders a LaTeX math string to an SVG file using the existing `pdflatex` + `dvisvgm` pipeline, but skips the slow Inkscape PNG rasterisation step. It returns placement metadata (`width`, `height`, `x_offset`, `y_offset`) plus the SVG's intrinsic dimensions (`native_w`, `native_h`).

### 20.2 Backend: `SlidesBuilder.add_image`

[`SlidesBuilder.add_image()`](slides_builder.py:233) emits a Google Slides image placeholder (`shapeTypeId = 3`) with the style keys observed in native equation copies:

* `15` — placeholder fill color (`#EEEEEE`)
* `177` — image placeholder flag (`0`)
* `19` — border color (`#595959`)
* `22` — border weight (`381` centipoints)
* `39` — image source URL
* `49` — blob ID (`s-blob-v1-IMAGE-...`)
* `8` / `9` — native image width/height

The transform scale is computed as `(width_pt * CP) / native_width_px`, matching the native equation capture.

### 20.3 Auxiliary Clipboard MIME Types

When images are added, [`SlidesBuilder.to_punch()`](slides_builder.py:287) now also produces:

* `application/x-vnd.google-docs-document-slice-clip+wrapped` — an entity map with inline image entities (`eo_type: 0`, `i_src`, `i_cid`, dimensions, crop info).
* `application/x-vnd.google-docs-image-clip+wrapped` — maps each blob ID to its image URL and a `cosmo_ids` entry.

These match the three-MIME native equation clipboard format.

### 20.4 Backend: SVG Rendering and Google Drive Upload

[`app.py`](app.py:280):

* Imports `compile_latex_to_svg` (optional) and adds `_svg_dimensions()` and `_upload_svg_to_drive()` helpers.
* In `convert_to_google_slides_json()`, text elements with `isLatex`/`is_latex` are rendered to SVG.
* Google Slides **does not accept data URLs** for pasted images (it shows "error rendering shape rectangle"), so the SVG is uploaded to Google Drive with public read permissions and the `https://drive.google.com/uc?id=...&export=download` URL is used in the clipboard.
* Drive upload requires the user to be logged in. If no credentials are available, the equation falls back to plain text rendering and a warning is returned.
* An optional white background rectangle is added when `maskBg`/`mask_bg` is enabled.
* `/api/compile_clipboard` returns the extra MIME payloads when image equations are present.

### 20.5 Frontend: Writing Extra MIME Types

[`templates/index.html`](templates/index.html:3275):

* `executeBrowserCopy()` accepts an optional `extraMimes` object and writes the document-slice and image-clip MIME entries alongside the drawings-object wrapper.
* `copyToGoogleSlides()` forwards `document_slice_wrapped` and `image_clip_wrapped` from the server response.
* Added a `warning` status style (yellow) for renderer/auth fallback messages.

### 20.6 Test Results

* [`test_latex_clipboard_builder.py`](test_latex_clipboard_builder.py:1) confirms the builder emits the correct shape type 3 op, blob ID, and auxiliary MIME payloads.
* Direct invocation of `compile_latex_to_svg(r'x(t)', 16, '#000000', 'center')` successfully produces an SVG file and placement metadata.
* A direct clipboard test with a base64 data URL failed in Google Slides with "error rendering shape rectangle", confirming that image placeholders require a real hosted URL.
* Fallback to plain text rendering works when no Google credentials are available.
* Image placeholders do **not** register the shape ID in `autotext_content`, matching the native Google Slides equation capture.

### 20.7 Next Step

Restart the Flask server, log in via the site, then copy a LaTeX-containing preset (e.g. Lorenz Attractor or Parametric) and paste into Google Slides. Alternatively, run `python write_latex_test_to_clipboard.py` with a valid `token.json` in the project folder; it uploads the test SVG to Drive and writes the clipboard directly. If equations still fail, capture the clipboard with `python extract_last_copy.py` and share the result.

## 21. Summary of GSlides LaTeX Image Embedding & Split-Copy Workflows (2026-06-13)

### 21.1 Findings on Image Embedding Restriction
* **GSlides Wrapper Signature Verification:** Our diagnostic comparisons (using `write_latex_native_with_generated_wrappers.py` against exact native traces) conclusively proved that Google Slides validates drawing wrappers (`application/x-vnd.google-docs-drawings-object+wrapped`) when image placeholders are present.
* **Signature Cryptographic Locks:** Specifically, the `dih`, `edi`, and `edrk` keys contain cryptographic/checksum hashes generated internally by Slides. When a third-party app compiles image-clips with custom/dummy wrappers, GSlides refuses to fetch the image (even if hosted publicly on Google Drive) and throws a **"Problem retrieving the image"** fallback error.
* **Resolution:** Embedding external raster image URLs inside the GWT vector payload programmatically is locked out.

### 21.2 The Split-Copy Architecture Solution
To bypass this limitation without sacrificing either **native shapes editability** or **LaTeX mathematical display quality**, we built a dual-channel copy pipeline:
1. **The Vector Base:** Clicking the main **Copy to Google Slides** button compiles the editable native shapes (grid lines, axes, title textboxes, curves, hatches, markers, etc.) using `SlidesBuilder` and ignores LaTeX equations. This copies perfect, crisp, grouped native Slide vectors.
2. **The Equation Overlay:**
   - Any `isLatex` text element is compiled dynamically by the backend into a standalone, styled, transparent-background SVG (using `compile_latex_to_svg`) matching the selected color and font size.
   - These rendered equations are shown on the left sidebar under a reactive, collapsible fold-out panel: **LaTeX Equations (Copy/Drag SVG)**.
   - The SVG is rendered inside an `<img>` tag on the client using a base64 Data URL, allowing the user to simply **right-click -> Copy Image** or **drag-and-drop** the transparent vector-supported equations directly into their active Slide.
   - A fallback button **Copy as PNG** uses `navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])` to write a high-resolution transparent PNG of the equation to the clipboard in 1 click.


