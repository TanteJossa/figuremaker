# Extensive Analysis Plan: Deterministic Figuremaker Pipeline

This plan outlines the visual rules, architectural design, and implementation strategy for building a deterministic, Python-based figuremaker that supports mathematical functions and natively renders to Google Slides/Drawings using the `AtomicDiagramGenerator` API.

## 1. Visual & Stylistic Rules (Extracted from Examples)
Based on the analysis of the `Jaarlijkse plastic productie` (stacked area) and the `(x,t)-grafiek` (piecewise linear), the following styling rules apply:

*   **Typography:** The primary font is **Ubuntu**. Axis labels and units may have varied weights (e.g., **x** (km)). Legend texts and tick labels are typically regular weight.
*   **Axes & Borders:**
    *   Some charts use a full rectangular bounding box (thick black stroke).
    *   Others use a simple L-shaped axis (bottom and left only).
    *   Axes are solid, cleanly defined lines.
*   **Gridlines:** 
    *   Major gridlines are thin and dashed (e.g., dark gray).
    *   Minor gridlines (if present) are lighter dashed lines.
    *   Gridlines align perfectly with axis tick values.
*   **Data Representation:**
    *   **Lines:** Function lines are bold/thick (e.g., 2-3pt) to stand out against the grid. Piecewise linear charts have crisp corners.
    *   **Areas:** Shaded regions use solid fills without borders. Stacked charts use contrasting brand colors (Red, Blue, Green, Gray, Orange).
*   **Annotations:**
    *   **Legends:** Positioned horizontally at the bottom, often enclosed in a thin rectangular border. They use square color swatches followed by text.
    *   **Top Arrows:** Phase indicators (like A, B, C, D, E) are drawn above the graph using horizontal arrows with the label centered above or inside the arrow gap, typically in a bold, distinct color like yellow/gold.

## 2. Architectural Design
The architecture is inspired by Matplotlib (Artist-Backend separation) and Plotly (Declarative Data Models mapping to Renderers). It consists of three primary layers:

### Layer 1: Configuration / Declarative API
User-facing Python classes where the graph's intent is defined independently of its pixel representation.
*   `Figure`: The main container, handling size, background, and managing grids (like the 2x3 graph layout).
*   `PlotArea`: Represents a single coordinate system. Defines `x_range`, `y_range`, `x_ticks`, `y_ticks`.
*   **Logical Elements:**
    *   `FunctionLine(func, domain)`: A continuous math function.
    *   `PiecewiseLine(points)`: Connected coordinates.
    *   `ShadedArea(func1, func2, domain)`: Fills space between functions or axis.
    *   `StackedArea(data_series)`: Computes stacked y-values.
    *   `Point(x, y, label)`: Important markers (snij/raakpunten).
    *   `TopArrows(phases)`: Timeline/phase indicators at the top.

### Layer 2: Geometry & Math Engine
Translates abstract mathematical concepts into concrete physical shapes.
*   **Coordinate Transformer:** Maps logical domain `[x_min, x_max]` and `[y_min, y_max]` to canvas PT boundaries `[left, right]` and `[bottom, top]`.
*   **Function Evaluator:** Uses NumPy (or math) to discretize mathematical functions into an array of `(x, y)` tuples.
*   **Calculus Utilities:** Calculates intersections, bounding boxes, and derivatives for tangent lines (`raaklijn`).

### Layer 3: Render / Backend (AtomicDiagramGenerator)
Maps the physical geometries into Google Slides/Drawings native elements via our existing `AtomicDiagramGenerator` API.
*   Discretized arrays become `Polyline` objects.
*   Shaded areas become filled `Polygon`/`Shape` objects.
*   Text and labels become `TextBox` objects with precise PT coordinates.
*   Axes and Gridlines become standard `Line` objects with `dasharray` equivalents.

## 3. Implementation Strategy
Development should proceed in the following structured phases:

*   **Phase 1: Core Engine & Coordinate Transformation**
    *   Create the `CoordinateTransformer` class.
    *   Implement function discretization (turning a lambda into XY points).
    *   *Output:* Ability to calculate PT coordinates accurately.

*   **Phase 2: Base Axes, Grid, and Line Rendering**
    *   Build `PlotArea` and render X/Y axes and ticks.
    *   Implement dashed gridlines.
    *   Translate `PiecewiseLine` and `FunctionLine` into `AtomicDiagramGenerator` lines.
    *   *Output:* Capable of rendering a basic line chart with grid and axes.

*   **Phase 3: Areas, Polygons, and Stacking**
    *   Implement `ShadedArea` (generating closed polygons).
    *   Implement logic for `StackedArea` charts.
    *   Create the Legend generator.
    *   *Output:* Capable of rendering the stacked plastic production chart.

*   **Phase 4: Annotations & Calculus (Tangents/Intersections)**
    *   Implement Points, custom labels, and `TopArrows`.
    *   Add numeric utilities for tangent lines (`raaklijn`) and orthogonal lines.
    *   *Output:* Capable of rendering the (x,t)-grafiek and Sinusoid with tangents.

*   **Phase 5: High-Level Graph Types & Layouts**
    *   Create wrapper templates for specific graph types (Sinusoid, Grid 2x3, Stacked Area, x-t graph).
    *   Finalize styling configurations (colors, font imports).
    *   *Output:* Complete deterministic pipeline meeting all user requirements.