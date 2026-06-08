# Python-Based Deterministic Graph Generator Architecture

## 1. Executive Summary
As the project shifts from an AI-dependent SVG/EMF pipeline to a deterministic generation model, we require a robust Python-based architecture capable of producing precise, educational graphs. This new system directly utilizes the `AtomicDiagramGenerator` API wrapper to draw native, editable vectors (lines, text, and basic shapes) directly onto Google Slides/Drawings.

This document outlines the architecture required to map mathematical inputs into scalable presentation coordinates, the JSON/DSL configuration model, and the strategies for rendering complex elements like curves and area shading natively.

---

## 2. High-Level Architecture Pipeline

The graph generator operates in four sequential stages:

1.  **Configuration Parser (Input):** Accepts a deterministic JSON configuration or Python DSL defining the axes, formulas, points, and styling.
2.  **Mathematical Evaluator:** Parses mathematical string expressions (e.g., `sin(x)`) into Python callables using `sympy` or standard `math`, computes intersections, and evaluates derivatives for tangent lines.
3.  **Viewport Mapping (Coordinate Transform):** Transforms abstract mathematical domains (e.g., `X: -10 to 10`) into absolute Presentation Point (PT) coordinates required by Google's API, applying necessary scaling, Y-axis inversion, and margins.
4.  **Native Renderer:** Generates the specific Google Workspace JSON commands (using `AtomicDiagramGenerator`) for grids, lines, text labels, and hatched areas, queueing them for a final atomic commit.

---

## 3. Configuration Interface (JSON Schema / DSL)

To replace the prompt-based AI generation, the system will use a highly typed JSON schema (or equivalent Python Pydantic models). This allows either human configuration or a web UI to deterministically generate graphs.

### Example Schema (Area under a Curve & Tangent)
```json
{
  "meta": {
    "title": "Velocity over Time",
    "size": "medium",  // Resolves to e.g., 400x300 PT
    "theme_overrides": {}
  },
  "axes": {
    "x": {
      "min": 0, "max": 10, "step": 1,
      "label": "t (s)", "show_grid": true
    },
    "y": {
      "min": -5, "max": 20, "step": 5,
      "label": "v (m/s)", "show_grid": true
    }
  },
  "plots": [
    {
      "id": "v_curve",
      "type": "formula",
      "formula": "2 * x * sin(x) + 5",
      "color": "blue_primary",
      "weight": 3
    },
    {
      "id": "v_tangent",
      "type": "tangent",
      "target": "v_curve",
      "at_x": 4.5,
      "color": "red_primary",
      "dash_style": "DASHED"
    }
  ],
  "areas": [
    {
      "type": "fill_between",
      "top": "v_curve",
      "bottom": 0, // Maps to x-axis
      "x_start": 2,
      "x_end": 8,
      "style": "hatch", // Native rendering workaround
      "color": "blue_bg"
    }
  ],
  "points": [
    {
      "x": 4.5, 
      "y": "eval(v_curve)", // Dynamic calculation based on curve
      "label": "A", 
      "show_dot": true
    }
  ]
}
```

---

## 4. Mathematical-to-Presentation Coordinate Mapping

The `Viewport` class handles the translation between Cartesian math coordinates and Google Workspace canvas coordinates (PT).

### 4.1. Coordinate Inversion & Scaling
Google Workspace uses a coordinate system where `(0,0) PT` is the top-left corner, and Y increases downwards. Mathematical graphs assume Y increases upwards.

```python
class Viewport:
    def __init__(self, config, canvas_width, canvas_height, margins):
        # canvas dimensions in PT
        self.w = canvas_width - margins.left - margins.right
        self.h = canvas_height - margins.top - margins.bottom
        
        # math dimensions
        self.math_x_min = config.axes.x.min
        self.math_x_range = config.axes.x.max - config.axes.x.min
        
        self.math_y_min = config.axes.y.min
        self.math_y_range = config.axes.y.max - config.axes.y.min
        
        self.margins = margins

    def map_x(self, math_x: float) -> float:
        scale = self.w / self.math_x_range
        return self.margins.left + ((math_x - self.math_x_min) * scale)

    def map_y(self, math_y: float) -> float:
        scale = self.h / self.math_y_range
        # Invert Y axis: subtract mapped value from total height
        return self.margins.top + self.h - ((math_y - self.math_y_min) * scale)
```

### 4.2. Margins and Axis Cutoffs
To ensure axis labels (e.g., numbers "10", "20") do not fall off the slide, the viewport enforces a padding area. The absolute coordinates of the center `(0,0)` in math logic are resolved properly regardless of whether they fall in the middle of the graph or off-screen (e.g., if the range is `X: 10 to 50`, the Y-axis line is drawn at `X=0` mathematically, which the viewport calculates as outside the bounding box and thus suppresses rendering).

---

## 5. Rendering Strategies & API Translation

Google Slides API has limited support for complex freeform paths and custom polygons. The Renderer abstracts these limitations using intelligent workarounds mapped to `AtomicDiagramGenerator`.

### 5.1. Curves and Functions
Since the `createLine` command only generates straight lines, non-linear curves (like sinusoids) are rendered through **linear interpolation (segmentation)**.
*   **Logic:** The Renderer evaluates the math function at $N$ intervals (e.g., $N=100$). It generates $N-1$ short, continuous `createLine` commands queued into `AtomicDiagramGenerator`.
*   Because the save is atomic, generating 100 line segments is virtually instantaneous and creates the illusion of a smooth curve.

### 5.2. Areas (Arceren)
Because `createShape` does not support complex, multi-point polygon paths for filling the area under a curve natively via the REST API, we use a **hatching technique**:
*   **Logic:** To shade an area between `f(x)` and the X-axis from $x_1$ to $x_2$, the Renderer generates a dense array of parallel vertical or diagonal lines (e.g., every 0.2 math units).
*   This creates an authentic, educational "arceren" (shading) aesthetic.
*   *Alternative:* If the WAC protocol (undocumented endpoint) is used, we can investigate emitting `POLYLINE` or `FREEFORM` shape definitions. For the standard API, hatching is robust.

### 5.3. Tangents and Orthogonals
*   **Tangents:** Evaluated mathematically via the derivative at point `X`. A straight line is extrapolated covering the viewport bounds and rendered using a `DASHED` line property.

### 5.4. Data Points & Labels
*   **Points:** Rendered using `createShape` of type `ELLIPSE`, mapping math `(X,Y)` to the center of the shape, offset by the radius.
*   **Labels:** Using `queue_text_box`. The text is offset from the point coordinate by predefined padding (e.g., `+10 PT` on X and Y) to prevent overlapping with the line.

---

## 6. Fulfillment of Graph Types
*   **Sinusoide with Tangent Lines:** Uses formula evaluation (segmentation) and derivative calculation at user-specified points.
*   **Area under curve:** Uses the `fill_between` configuration resulting in native line hatching.
*   **(x,t) graphs with phases:** Support for piece-wise functions (e.g., `[ {"x_range": [0, 5], "formula": "2*x"}, {"x_range": [5, 10], "formula": "10"} ]`).
*   **Stacked line charts with legends:** Multiple plot configurations combined with an auto-generated Legend box (using `createShape` for a background and `insertText` for keys).
