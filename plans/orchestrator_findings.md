# Orchestrator Findings: Programmatic Google Drawings Text & Arrows Modification

## Executive Summary
This document summarizes our reverse-engineering and successful implementation of programmatic native shape creation and text insertion inside Google Drawings. We have proved that the previous vector-based SVG-to-EMF approach, which converted text to uneditable vector paths, can be completely replaced by interacting directly with the undocumented real-time Google Drawings Save API (WAC protocol). This allows us to insert fully editable, natively styled text boxes and arrow lines.

---

## 1. Google Drawings Save API Architecture
Google Drawings, Google Slides, and Google Docs use a shared real-time operational transformation (OT) editor backend. When modifications are made, the browser sends small delta operation batches to the `/save` endpoint of the document:
```
POST https://docs.google.com/drawings/u/0/d/{drawing_id}/save
```

### 1.1 Authentication Constraints
* **Session Cookies (Mandatory for Edits):** The save endpoint `/save` **does not** accept standard OAuth 2.0 Bearer tokens in the `Authorization` header for making modifications (returns `HTTP 403 Forbidden`). Writes/saves strictly require standard Google browser session cookies (`SID`, `HSID`, `SSID`, etc.) passed via the `Cookie` header.
* **Access Tokens (GET only):** Standard OAuth Access tokens are only sufficient for reading and exporting drawings (e.g. GET `/edit`), but not for `/save`.
* **Cross-Site Protection (X-Same-Domain):** Save requests require the header `X-Same-Domain: 1` and appropriate `Referer` / `Origin` headers to pass backend checks.

### 1.2 Session and Revision State
* **CSRF Edit Token:** An active edit session token (format `{some_base64_like_string}:{13_digit_timestamp}`) must be parsed from the `/edit` HTML page (embedded in global JS variables).
* **Document Revision (rev):** The server maintains a strict incrementing revision counter. Each save request must match the current document revision (`rev`). If there's a mismatch, the server returns `HTTP 550` along with the expected revision number (e.g. `[["er",...,550,...,expected_rev]]`), requiring operational transformation conflict resolution or client revision increment.
* **Session ID (sid) & Request ID (reqId):** A unique hex session identifier `sid` is generated for the duration of the editor session. The `reqId` starts at 0 and increments for each subsequent save operation in that session.

---

## 2. Reverse-Engineered OT Commands Schema

Operations are serialized as a JSON array of session bundles under the `bundles` form parameter:
```json
[
  {
    "commands": [...],
    "sid": "session_id",
    "reqId": 0
  }
]
```

### 2.1 Inserting a Styled Textbox Shape (Shape Type 153)
* **Command ID:** `3`
* **Syntax:** `[3, element_id, shape_type, affine_transform_matrix, properties_array, parent_id]`
* **Example:**
```json
[
  3, 
  "g_textbox_0_0", 
  153, 
  [1.8092, 0, 0, 1.0554, 100000, 100000], 
  [
    14, 0, 
    15, "#CFE2F3",
    19, "#000000",
    22, 381, 
    27, 1.3, 
    30, 1.3, 
    51, ["", 0], 
    52, ["", 0]
  ], 
  "p"
]
```
* **Parameters Decoded:**
  * `153`: Google Drawings shape code for Textbox/Rectangle.
  * `[scaleX, skewY, skewX, scaleY, translateX, translateY]`: Affine 2D transform setting position and scaling/dimensions in EMUs (English Metric Units).
  * Properties Flat Array:
    * `15`: `#CFE2F3` - Solid Fill Color (light blue background).
    * `19`: `#000000` - Border/Stroke Color (black).
    * `22`: `381` - Border weight.
    * `51` / `52`: Textbox padding/wrapping properties.
  * `"p"`: Parent page/canvas element.

### 2.2 Adding Text to a Shape (Atomic Transaction)
Shapes do not contain text frames by default. Writing text to a shape is a two-step operational sequence that must be executed atomically inside a transaction block (group command code `4`):
* **Transaction ID:** `4`
* **Create Text Story (Command 16):** Initializes the text run story on the element.
* **Insert String (Command 15):** Inserts the string content at the desired offset.
* **Example:**
```json
[
  4,
  [
    [16, "g_textbox_0_0", null, 0, 23],
    [15, "g_textbox_0_0", null, 0, "Hello, Google Drawings!"]
  ]
]
```
* **Parameters Decoded:**
  * `16`: Initialize text story. Third param is `null` (default story). Fourth param is start offset `0`. Fifth param is final text length `23`.
  * `15`: Insert text run. Third param is `null`. Fourth param is insertion offset index `0` (must match the existing story boundaries to avoid `HTTP 550` out-of-bounds error). Fifth param is string value.

### 2.3 Creating a Styled Arrow Line (Shape Type 108)
Lines and connection lines are created using shape type `108`. Arrowhead styling is configured via property IDs `165` and `166`:
* **Create Connection Line:**
```json
[
  4, 
  [
    [
      3, 
      "g_arrow_0_1", 
      108, 
      [1.7074, 0, 0, 0.2738, 250000, 100000], 
      [
          165, 2,  // Start point / connection
          166, 1,  // End Arrow Head Style (1 = arrow)
          44, 0, 
          45, 1
      ]
    ], 
    "p"
  ]
]
```
* **Update Line Geometry/Transform:**
```json
[6, "g_arrow_0_1", [1.7074, 0, 0, 0.1334, 250000, 100000]]
```

---

## 3. Redesigning Application Flow around Private API Approach

Instead of performing expensive and lossy SVG-to-EMF conversions, the application flow can be simplified and improved:

### 3.1 New Pipeline Architecture
```
[User Text/Arrow Prompt]
          │
          ▼
   [Gemini model]  ──► Generates list of objective visual metaphors, positions & text
          │
          ▼
[OT Commands Builder] ──► Converts visual metaphors to Google OT commands (codes 3, 16, 15, 4)
          │
          ▼
 [Drawing Sync Engine] ──► Fetches CSRF/Revision -> Executes sequential save requests
          │
          ▼
[Natively Rendered, 100% Editable Google Drawing]
```

### 3.2 Key Redesign Advantages
1. **100% Editable:** Shapes, arrow lines, and text boxes are natively drawn on Google Drawings canvas, meaning users can edit text, recolor shapes, resize arrows, and move elements around directly inside Google Drawings or Google Slides without any clipping or vector-path flattening.
2. **Platform Native Styling:** Leverage Google Drawings' standard fonts, drop shadows, gradient fills, and arrowhead styles natively.
3. **Zero External Dependencies:** No need for local installations of Inkscape, LibreOffice, or other heavy command-line vector converters.
4. **Blazing Fast Performance:** Conversions and uploads are replaced by simple, ultra-lightweight POST requests, completing in fractions of a second.
