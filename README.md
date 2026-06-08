# Leerlevels Figuremaker

A robust, deterministic, python-based programmatic graph and diagram generator designed to produce precise, high-quality, and natively editable educational figures. The system translates mathematical models directly into scalable vector primitives and uploads them natively into Google Slides and Google Drawings.

---

## 🚀 Key Architectural Concepts

### 1. Shift from AI-Dependent to Deterministic Vector Models
Earlier iterations relied on prompt-based AI rendering to output raw SVGs/EMFs. This created uneditable, flat, and unpredictable assets. This version implements a strictly **deterministic programmatic architecture**:
* It evaluates exact mathematical functions (curves, tangents, differential equations) and converts them into precise coordinates.
* Generates fully editable, natively styled shapes, lines, arrows, and text boxes directly onto the Google Slides/Drawings canvas.

### 2. Viewport Coordinate Transform Mapping
Google Slides uses a canvas system measured in absolute **Presentation Points (PT)**, where `(0,0)` is the top-left corner and $Y$ increases downwards. Mathematical Cartesian coordinate systems have $Y$ increasing upwards.
The system features a custom [`Viewport`](graph_engine.py) mapping coordinator:
* **Translation:** Maps abstract domains (e.g., $X \in [-10, 10]$, $Y \in [-5, 20]$) into target canvas point coordinates (PT).
* **Axis Inversion:** Inverts the $Y$ coordinate logic dynamically for presentation display.
* **Smart Bounds & Margins:** Prevents numerical labels from running off-canvas and auto-suppresses components that fall out of viewport bounds.

### 3. Google REST API Curve Segmentation & Shading
Because the Google Slides API lacks native support for complex freeform paths or multi-point shading polygons:
* **Curve Segmentation:** Non-linear functions (like sinusoids) are plotted by evaluating the formulas over $N$ fine intervals (e.g., $N=100$), generating short, consecutive line segment operations. The batch is submitted atomically to create the visual appearance of a perfectly smooth curve.
* **Area Hatching ("Arceren"):** Shading areas under curves is accomplished via custom hatching—drawing a dense array of parallel vertical/diagonal line structures, creating a clean, authentic, and educational aesthetic.

### 4. Undocumented Google Drawings Save API (WAC Protocol)
For direct modifications inside Google Drawings (where standard Google REST APIs are extremely limited):
* Programmatic insertion of editable shapes, lines, connections, and arrows uses the real-time operational transformation (OT) **WAC Save Protocol** (`/save` endpoint).
* Handles active session cookies, document revision counters (`rev`), unique session/request ID increments, and transaction blocks.

---

## 📁 Repository Structure

* [`app.py`](app.py): Flask application offering an interactive web playground, managing Google OAuth flow session credentials, and driving the web interface.
* [`graph_engine.py`](graph_engine.py): The core mathematical evaluator, viewport mapper, grid builder, and SVG generator.
* [`leerlevels_style.py`](leerlevels_style.py): Shared styles, color palette declarations (with corresponding slide hex translators), and line/text properties.
* [`gslides_uploader.py`](gslides_uploader.py): Connects to the Google Slides and Drive REST APIs to draw native, editable shapes, text frames, and lines using standard authentication.
* [`prompt_template.py`](prompt_template.py): System prompts for integrating LLM/Gemini assistance (e.g., parsing user requests into deterministic JSON definitions).
* [`Dockerfile`](Dockerfile): Multi-layered slim Debian container installing standard Python packages along with system-level LaTeX engines (`texlive-latex-base`, `texlive-fonts-recommended`, `texlive-extra-utils`, `texlive-latex-extra`, `texlive-science`), `dvisvgm`, and `inkscape` for programmatic high-fidelity SVG/PDF vector conversions.
* [`deploy.bat`](deploy.bat): Command-line helper to build and push containerized builds onto Google Cloud Run.
* [`templates/index.html`](templates/index.html): Interactive web frontend UI for previewing and pushing generated graphs.
* [`test_*.py` Scripts](.): A complete suite of programmatic math test cases demonstrating:
  * Area shading under curved paths (`test_graph_area.py`)
  * Differential equations (`test_graph_diffeq.py`)
  * Multi-column coordinate grids (`test_graph_grid.py`)
  * Piecewise phase-based graphs (`test_graph_phases.py`)
  * Sine-wave plots with tangents (`test_graph_sinus.py`)
  * Multi-curve stacked plots (`test_graph_stacked.py`)
  * Custom arrows & boxes (`test_graph_new_features.py`)

---

## ⚙️ Setup and Installation

### 1. Prerequisites

Ensure your system has the following dependencies:
* **Python 3.11** or higher.
* **LaTeX suite** (with `dvisvgm` and `latex` available on path) if LaTeX mathematical formula text box labels are used.
* **Inkscape** (if converting vector types programmatically).

For Debian/Ubuntu systems, you can install these via `apt`:
```bash
sudo apt-get update
sudo apt-get install -y texlive-latex-base texlive-fonts-recommended texlive-extra-utils texlive-latex-extra texlive-science dvisvgm inkscape
```

### 2. Python Virtual Environment Setup

1. Clone this repository:
   ```bash
   git clone <repository_url>
   cd figuremaker
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # On Windows (CMD/PowerShell)
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```
3. Install package requirements:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### 3. Environment Configurations

1. Copy the template configuration file:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill out your variables:
   * `GEMINI_API_KEY`: Your Google Gemini API Key (used for optional AI generation of JSON chart setups).
   * `DRIVE_FOLDER_ID`: The default Google Drive folder ID where drawings/slides should be uploaded.

---

## 🔑 Authentication Credentials

This app leverages Google OAuth/Service Account protocols. For the app to interact with Google Slides/Drive, you should place credentials in the project root (safely ignored by Git):

### Option A: Standard OAuth Web Flow (Recommended for local dev)
Place your Web Application OAuth client secret file as `credentials.json` in the root folder. You can obtain this from the **Google Cloud Console** under API & Services > Credentials (configured with Google Drive & Slides scopes). 

On first run, the app will redirect to a Google Login screen to complete OAuth authentication. The session is cached locally as `token.json`.

### Option B: Google Service Account
Provide a Service Account key file as `service_account.json` in the root folder. The slides and drive uploaders will automatically detect this and run in headless, non-interactive authentication mode (perfect for background services or cron jobs). Ensure you share your target Google Drive folders with the service account email.

---

## 🏃 Running the Application

### Launching the Web Interface
Start the local Flask server:
```bash
python app.py
```
By default, the server runs on `http://127.0.0.1:5000` (or `http://localhost:8080` in containerized environments). Open this URL in your web browser to play around with the graph templates, render previews, and export them natively to Google Slides.

### Executing Math Figure Tests
You can run any test script directly in your terminal. This creates programmatic SVG and structural JSON descriptions of the math graphs:
```bash
python test_graph_sinus.py
python test_graph_area.py
```

---

## 🐳 Containerization & Deployment

### Run Locally with Docker
1. Build the Docker container image:
   ```bash
   docker build -t leerlevels-figuremaker .
   ```
2. Run the container:
   ```bash
   docker run -p 8080:8080 --env-file .env leerlevels-figuremaker
   ```

### Deploying to Google Cloud Run
A convenient script is configured in `deploy.bat` to build and deploy to Google Cloud Run (located under project `joost-koch`, region `europe-west4`). Run:
```cmd
deploy.bat
```
Ensure you have the Google Cloud CLI (`gcloud`) installed, authorized, and configured with appropriate service roles.
