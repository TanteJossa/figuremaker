import os
import subprocess
import tempfile
import traceback
import logging
import json
import uuid
import base64
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from dotenv import load_dotenv
import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from slides_builder import SlidesBuilder

# Optional LaTeX renderer used for clipboard image equations.
try:
    from graph_engine import compile_latex_to_png, compile_latex_to_svg
    LATEX_RENDERER_AVAILABLE = True
except (ImportError, FileNotFoundError):
    compile_latex_to_png = None
    compile_latex_to_svg = None
    LATEX_RENDERER_AVAILABLE = False

# Allow insecure transport for local development (OAuth over HTTP)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Allow relaxed token scope in oauthlib to avoid crashed callbacks if Google returns additional scopes (like email/profile)
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# We need both Drive and Slides scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/presentations'
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("figuremaker")

logger.info("========================================")
logger.info("Initializing figuremaker Flask app...")
logger.info("========================================")

# Load environment variables
load_dotenv()

# Diagnostic startup logging to validate Docker/Cloud Run environment
logger.info("--- Environment Variable Check ---")
logger.info(f"PORT (defined by Cloud Run): {os.environ.get('PORT', 'Not set (defaulting to 5000/8080 depending on runner)')}")
logger.info(f"FLASK_SECRET_KEY: {'Configured' if 'FLASK_SECRET_KEY' in os.environ else 'Using default'}")
logger.info(f"GEMINI_API_KEY: {'Configured' if 'GEMINI_API_KEY' in os.environ else 'Not configured (AI features may fail)'}")
logger.info(f"DRIVE_FOLDER_ID: {os.environ.get('DRIVE_FOLDER_ID', 'Not configured (using root folder as default)')}")

# Check key files in workspace
logger.info("--- File System Check ---")
for filename in ['credentials.json', 'service_account.json', '.env']:
    exists = os.path.exists(filename)
    logger.info(f"File '{filename}' exists: {exists}")

# Attempt to import Gemini official client SDK
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Import converters and uploaders
try:
    from converter import svg_to_emf
    CONVERTER_AVAILABLE = True
except ImportError:
    CONVERTER_AVAILABLE = False

try:
    from gdrive_uploader import GoogleDrawingsUploader
    GDRIVE_AVAILABLE = True
except (ImportError, FileNotFoundError):
    GDRIVE_AVAILABLE = False

try:
    from gslides_uploader import GoogleSlidesUploader
    GSLIDES_AVAILABLE = True
except (ImportError, FileNotFoundError):
    GSLIDES_AVAILABLE = False

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "leerlevels-secret-key-change-me")

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_credentials():
    if 'credentials' not in session:
        return None
    creds_data = session['credentials']
    creds = Credentials(
        token=creds_data.get('token'),
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data.get('token_uri'),
        client_id=creds_data.get('client_id'),
        client_secret=creds_data.get('client_secret'),
        scopes=creds_data.get('scopes')
    )
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        try:
            creds.refresh(Request())
            session['credentials'] = credentials_to_dict(creds)
        except Exception as e:
            logger.error(f"Failed to refresh credentials: {e}")
            return None
    return creds

@app.route('/login')
def login():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES
    )
    redirect_uri = url_for('oauth2callback', _external=True)
    if not request.is_secure and 'localhost' not in redirect_uri and '127.0.0.1' not in redirect_uri:
        redirect_uri = redirect_uri.replace('http://', 'https://')
    flow.redirect_uri = redirect_uri
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['state'] = state
    if hasattr(flow, 'code_verifier'):
        session['code_verifier'] = flow.code_verifier
        logger.info(f"Saved code_verifier to session: {flow.code_verifier}")
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    logger.info("Handling OAuth2 Callback...")
    try:
        state = session.get('state')
        if not state:
            logger.error("No state in session. Cannot proceed.")
            return "No state in session. Please try logging in again.", 400
            
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            'credentials.json',
            scopes=SCOPES,
            state=state
        )
        redirect_uri = url_for('oauth2callback', _external=True)
        if not request.is_secure and 'localhost' not in redirect_uri and '127.0.0.1' not in redirect_uri:
            redirect_uri = redirect_uri.replace('http://', 'https://')
        flow.redirect_uri = redirect_uri
        
        # Restore code_verifier from session (crucial for PKCE verification)
        if 'code_verifier' in session:
            flow.code_verifier = session['code_verifier']
            logger.info("Restored code_verifier from session.")
        else:
            logger.warning("No code_verifier found in session.")
            
        authorization_response = request.url
        if not request.is_secure and 'localhost' not in authorization_response and '127.0.0.1' not in authorization_response:
            authorization_response = authorization_response.replace('http://', 'https://')
            
        logger.info(f"Generated flow redirect_uri: {flow.redirect_uri}")
        logger.info(f"Using authorization_response URL: {authorization_response}")
        
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        session['credentials'] = credentials_to_dict(credentials)
        logger.info("Google OAuth login successful!")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"OAuth callback failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "OAuth Callback Failed",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/logout')
def logout():
    session.pop('credentials', None)
    session.pop('state', None)
    return redirect(url_for('index'))

@app.route('/api/auth/status')
def auth_status():
    creds = get_credentials()
    if creds and creds.valid:
        return jsonify({"logged_in": True})
    return jsonify({"logged_in": False})

@app.route('/api/folders')
def list_folders():
    creds = get_credentials()
    if not creds:
        return jsonify({"error": "Unauthorized", "message": "Please log in first"}), 401
    try:
        parent = request.args.get('parent', 'root')
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Limit query to only folders directly inside the specified parent
        # This is crucial to avoid flatly listing millions of nested system/git directories
        query = f"mimeType = 'application/vnd.google-apps.folder' and '{parent}' in parents and trashed = false"
        
        results = drive_service.files().list(
            q=query,
            pageSize=1000,
            fields="nextPageToken, files(id, name)",
            orderBy="name"
        ).execute()
        folders = results.get('files', [])
        
        # Filter out system and hidden folder names
        ignored_names = {
            '.git', '.github', '.vscode', '.roo', 'node_modules', 'venv', 'env', 
            '__pycache__', 'temp_analysis', 'archive', 'examples'
        }
        filtered_folders = []
        for f in folders:
            name = f.get('name', '')
            if name.startswith('.') or name in ignored_names:
                continue
            filtered_folders.append(f)
            
        logger.info(f"Retrieved {len(folders)} direct child folders for parent '{parent}'; filtered to {len(filtered_folders)} valid destinations.")
        return jsonify({"success": True, "folders": filtered_folders})
    except Exception as e:
        logger.error(f"Error listing folders: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def _image_dimensions(local_path):
    """Return (width, height) in pixels for an image file."""
    from PIL import Image
    with Image.open(local_path) as img:
        return img.width, img.height


def _upload_image_to_drive(local_path, creds, folder_id=None, mime_type='image/png'):
    """
    Upload a local image to Google Drive, make it publicly readable, and return
    a direct download URL. Tries the Drive API webContentLink first, then falls
    back to the usercontent.google.com direct download URL.
    """
    from googleapiclient.http import MediaFileUpload

    drive_service = build('drive', 'v3', credentials=creds)
    file_metadata = {
        'name': os.path.basename(local_path),
        'mimeType': mime_type,
        'parents': [folder_id] if folder_id else []
    }
    media = MediaFileUpload(local_path, mimetype=mime_type)
    drive_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    file_id = drive_file.get('id')

    drive_service.permissions().create(
        fileId=file_id,
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()

    # Re-fetch to get the canonical direct download link used by Drive.
    file_metadata = drive_service.files().get(
        fileId=file_id,
        fields='webContentLink'
    ).execute()
    web_content_link = file_metadata.get('webContentLink')
    if web_content_link:
        return web_content_link
    return f"https://drive.usercontent.google.com/download?id={file_id}&export=download"


def convert_to_google_slides_json(elements, font_family='Ubuntu', include_latex=True):
    if not elements:
        return {
            "flat": json.dumps({"resolved": [], "unresolved": []}),
            "wrapped": json.dumps({"dih": 1245482604, "data": "{}"})
        }

    def get_element_z_index(el):
        if not el:
            return 1
        el_type = el.get('type', '')
        obj_id = str(el.get('id', '') or el.get('objectId', '')).lower()
        stroke = str(el.get('stroke', '')).lower()
        text = str(el.get('text', '') or '')

        # Layer 5 (Top): Graph Title
        is_title = el_type == 'text' and (
            'title' in obj_id or
            'lorenz' in text or 'lissajous' in text or 'overzicht' in text or
            (float(el.get('font_size', el.get('fontSize', 16)) or 16) >= 18 and el.get('bold') and not el.get('is_latex') and not el.get('isLatex'))
        )
        if is_title:
            return 5

        # Layer 2: LaTeX/Formula blocks and their backgrounds
        is_latex = el.get('is_latex') or el.get('isLatex') or 'latex' in obj_id or 'formula' in obj_id
        is_formula_bg = '_bg' in obj_id and ('text' in obj_id or 'latex' in obj_id or 'formula' in obj_id or 'element_102' in obj_id)
        if is_latex or is_formula_bg:
            return 2

        # Layer 0 (Bottom): Background Grid / Frame
        is_grid = 'grid' in obj_id or stroke == '#eeeeee' or stroke == '#dddddd' or el.get('dasharray') == '3,3' or el.get('dasharray') == '4,4'
        is_frame = 'frame' in obj_id or 'border' in obj_id or (el_type == 'rect' and 'grid' in obj_id)
        if is_grid or is_frame:
            return 0

        # Layer 3: Axes / Ticks
        is_axis = 'axes' in obj_id or 'axis' in obj_id or el_type in ('arrow', 'double_arrow')
        is_tick = 'tick' in obj_id or (el_type == 'line' and stroke == '#000000' and float(el.get('stroke_width', el.get('strokeWidth', 2.0)) or 2.0) == 1.5)
        if is_axis or is_tick:
            return 3

        # Layer 4: Labels / Numbers / Point Labels (Non-title text elements)
        if el_type == 'text':
            return 4

        # Layer 1: Plotted lines/curves/hatches/points/markers (falling through default)
        return 1

    valid_elements = [el for el in elements if el is not None]
    sorted_elements = sorted(valid_elements, key=get_element_z_index)

    builder = SlidesBuilder(font_family=font_family)

    for index, el in enumerate(sorted_elements):
        el_type = el.get('type')
        obj_id = el.get('id') or el.get('objectId') or f"element_{index}_{el_type}"

        if el_type == 'rect':
            builder.add_rect(
                x=el.get('x', 0),
                y=el.get('y', 0),
                width=el.get('width', 100),
                height=el.get('height', 100),
                fill=el.get('fill', 'none'),
                stroke=el.get('stroke', '#000000'),
                stroke_width=el.get('stroke_width', el.get('strokeWidth', 2.0)),
                obj_id=obj_id,
            )
        elif el_type in ('ellipse', 'circle'):
            builder.add_ellipse(
                x=el.get('x', 0),
                y=el.get('y', 0),
                width=el.get('width', 100),
                height=el.get('height', 100),
                fill=el.get('fill', 'none'),
                stroke=el.get('stroke', '#000000'),
                stroke_width=el.get('stroke_width', el.get('strokeWidth', 2.0)),
                obj_id=obj_id,
            )
        elif el_type in ('line', 'arrow', 'double_arrow'):
            builder.add_line(
                x1=el.get('x1', 0),
                y1=el.get('y1', 0),
                x2=el.get('x2', 0),
                y2=el.get('y2', 0),
                stroke=el.get('stroke', '#000000'),
                stroke_width=el.get('stroke_width', el.get('strokeWidth', 2.0)),
                dasharray=el.get('dasharray'),
                arrow_start=(el_type == 'double_arrow'),
                arrow_end=(el_type in ('arrow', 'double_arrow')),
                obj_id=obj_id,
            )
        elif el_type == 'text':
            is_latex = bool(el.get('is_latex') or el.get('isLatex'))
            if is_latex and not include_latex:
                continue
            text = str(el.get('text', ''))

            if is_latex and LATEX_RENDERER_AVAILABLE:
                try:
                    font_size = float(el.get('font_size', el.get('fontSize', 16)) or 16)
                    color = el.get('color', '#000000') or '#000000'
                    align = el.get('align', 'start') or 'start'
                    mask_bg = bool(el.get('mask_bg') or el.get('maskBg'))

                    latex_meta = compile_latex_to_png(text, font_size, color, align, group_id=obj_id)
                    if latex_meta:
                        local_path = latex_meta['local_path']

                        # Google Slides does not accept data URLs for pasted
                        # images; upload to Drive when the user is logged in.
                        creds = get_credentials()
                        if not creds:
                            logger.info(f"No Google credentials; skipping image LaTeX for '{text}'.")
                            raise RuntimeError("Google login required for LaTeX image paste")

                        image_url = _upload_image_to_drive(
                            local_path, creds,
                            folder_id=os.environ.get('DRIVE_FOLDER_ID'),
                            mime_type='image/png'
                        )

                        img_w = latex_meta['width']
                        img_h = latex_meta['height']
                        tx = float(el.get('x', 0)) + latex_meta['x_offset']
                        ty = float(el.get('y', 0)) + latex_meta['y_offset']
                        native_w, native_h = _image_dimensions(local_path)

                        if mask_bg:
                            builder.add_rect(
                                x=tx, y=ty,
                                width=img_w, height=img_h,
                                fill='#FFFFFF', stroke='none',
                                stroke_width=0,
                                obj_id=f"{obj_id}_bg"
                            )

                        builder.add_image(
                            x=tx, y=ty,
                            width_pt=img_w, height_pt=img_h,
                            image_url=image_url,
                            native_width_px=native_w,
                            native_height_px=native_h,
                            obj_id=obj_id
                        )
                        continue
                except Exception as e:
                    logger.error(f"Failed to render LaTeX image for '{text}': {e}")
                    # Fall through to regular text rendering as a safe fallback.

            builder.add_text(
                x=el.get('x', 0),
                y=el.get('y', 0),
                text=text,
                width=el.get('width'),
                height=el.get('height'),
                font_size=el.get('font_size', el.get('fontSize', 16)),
                color=el.get('color', '#000000'),
                align=el.get('align', 'start'),
                bold=el.get('bold'),
                italic=el.get('italic'),
                font_family=font_family,
                obj_id=obj_id,
            )
        elif el_type == 'group':
            builder.add_group(el.get('childrenObjectIds', []), obj_id=obj_id)

    return builder.to_punch()

@app.route('/api/compile_clipboard', methods=['POST'])
def compile_clipboard():
    logger.info("Received request to compile clipboard GWT payload.")
    data = request.json or {}
    elements = data.get("elements", [])
    font_family = data.get("fontFamily", "Ubuntu")

    # Warn callers when LaTeX equations are present but cannot be pasted as images.
    has_latex = any(
        bool(el.get('is_latex') or el.get('isLatex'))
        for el in elements if isinstance(el, dict)
    )
    creds = get_credentials()
    latex_warning = None
    if has_latex and not LATEX_RENDERER_AVAILABLE:
        latex_warning = "LaTeX renderer is unavailable; equations copied as plain text."
    elif has_latex and not creds:
        latex_warning = "LaTeX equations require Google login to paste as images; equations copied as plain text."
    
    try:
        compiled = convert_to_google_slides_json(elements, font_family, include_latex=False)
        clip_id = f"2519a9aa-7fff-ab00-1255-{uuid.uuid4().hex[:12]}"
        
        response = {
            "success": True,
            "flat": compiled["flat"],
            "wrapped": compiled["wrapped"],
            "clip_id": clip_id
        }
        if "document_slice_wrapped" in compiled:
            response["document_slice_wrapped"] = compiled["document_slice_wrapped"]
        if "image_clip_wrapped" in compiled:
            response["image_clip_wrapped"] = compiled["image_clip_wrapped"]
        if latex_warning:
            response["warning"] = latex_warning
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Failed to compile clipboard payload: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/compile_latex_images', methods=['POST'])
def compile_latex_images():
    """Render every LaTeX text element to a transparent PNG & SVG for raw image paste/drag."""
    logger.info("Received request to compile LaTeX images for clipboard.")
    data = request.json or {}
    elements = data.get("elements", [])

    if not LATEX_RENDERER_AVAILABLE or compile_latex_to_png is None:
        return jsonify({"success": False, "error": "LaTeX renderer not available"}), 500

    images = []
    try:
        for el in elements:
            if not isinstance(el, dict):
                continue
            if not (el.get('is_latex') or el.get('isLatex')):
                continue
            text = str(el.get('text', ''))
            font_size = float(el.get('font_size', el.get('fontSize', 16)) or 16)
            color = el.get('color', '#000000') or '#000000'
            align = el.get('align', 'start') or 'start'

            # 1. Compile to PNG
            latex_meta_png = compile_latex_to_png(text, font_size, color, align, group_id=el.get('id'))
            if not latex_meta_png:
                continue

            with open(latex_meta_png['local_path'], 'rb') as f:
                png_bytes = f.read()

            # 2. Compile to SVG (optional/best effort)
            svg_base64 = None
            if compile_latex_to_svg:
                try:
                    latex_meta_svg = compile_latex_to_svg(text, font_size, color, align, group_id=el.get('id'))
                    if latex_meta_svg and os.path.exists(latex_meta_svg['local_path']):
                        with open(latex_meta_svg['local_path'], 'rb') as f:
                            svg_bytes = f.read()
                        svg_base64 = base64.b64encode(svg_bytes).decode('ascii')
                except Exception as ex:
                    logger.warning(f"Failed to render LaTeX SVG fallback: {ex}")

            images.append({
                "text": text,
                "x": float(el.get('x', 0)),
                "y": float(el.get('y', 0)),
                "width": latex_meta_png['width'],
                "height": latex_meta_png['height'],
                "x_offset": latex_meta_png['x_offset'],
                "y_offset": latex_meta_png['y_offset'],
                "png_base64": base64.b64encode(png_bytes).decode('ascii'),
                "svg_base64": svg_base64,
            })

        return jsonify({"success": True, "images": images})
    except Exception as e:
        logger.error(f"Failed to compile LaTeX images: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

# Read the entire systems analysis file as prompt context
systems_analysis_content = ""
try:
    with open("drawings/leerlevels_systems_analysis.md", "r", encoding="utf-8") as f:
        systems_analysis_content = f.read()
except Exception:
    pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    logger.info("Received figure generation request via /api/generate.")
    if not GEMINI_AVAILABLE:
        return jsonify({
            "error": "Gemini SDK is not installed or available on this system.",
            "message": "Gemini SDK is not available. Please make sure Google GenAI is installed."
        }), 500

    data = request.json or {}
    prompt = data.get("prompt") or data.get("message")
    if not prompt:
        return jsonify({"error": "No prompt or message provided"}), 400

    try:
        from prompt_template import SYSTEM_PROMPT
        
        # Initialize Google GenAI client
        client = genai.Client()
        
        # Call Generate Content
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json"
            )
        )
        
        result_text = response.text
        logger.info(f"Gemini responded to generate: {result_text[:500]}...")
        
        result_json = json.loads(result_text)
        return jsonify(result_json)
        
    except Exception as e:
        logger.error(f"Gemini API generate call failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "message": f"AI error occurred during generation: {str(e)}. Please check your API key in .env or try again."
        }), 500

@app.route('/api/append', methods=['POST'])
@app.route('/api/append_slide', methods=['POST'])
def append_slide():
    logger.info("Received append slide request.")
    data = request.json or {}
    presentation_id = data.get("presentation_id")
    slide_data = data.get("slide_data")
    
    if not presentation_id:
        return jsonify({"error": "No presentation_id provided"}), 400
    if not slide_data:
        return jsonify({"error": "No slide_data provided"}), 400
        
    if GSLIDES_AVAILABLE:
        try:
            logger.info(f"Google Slides module available. Appending slide to presentation {presentation_id}...")
            # Use authenticated user credentials from session
            creds = get_credentials()
            if not creds:
                return jsonify({"error": "Unauthorized", "message": "Please log in with Google first"}), 401
                
            uploader = GoogleSlidesUploader(credentials=creds)
            file_obj = uploader.append_slide_from_canvas_data(presentation_id, slide_data)
            
            logger.info(f"Native Slide appended successfully! ID: {file_obj.get('id')}")
            return jsonify({
                "success": True,
                "url": file_obj.get("webViewLink"),
                "id": file_obj.get("id"),
                "is_slide": True
            })
        except Exception as e:
            logger.error(f"Google Slides API append failed: {str(e)}")
            import traceback
            print(traceback.format_exc())
            err_msg = str(e)
            return jsonify({
                "success": False,
                "error": err_msg,
                "message": f"Append error: {err_msg}"
            }), 500
    else:
        # Fallback Mock mode for append
        mock_slide_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit?usp=sharing"
        logger.warning("GSLIDES_AVAILABLE is False, mock appended")
        return jsonify({
            "success": True,
            "url": mock_slide_url,
            "id": presentation_id,
            "warning": "GSLIDES_AVAILABLE is False, mock appended",
            "message": "Appended in Fallback Mock mode."
        })

@app.route('/api/chat', methods=['POST'])
def chat():
    logger.info("Received chat command request.")
    if not GEMINI_AVAILABLE:
        return jsonify({
            "error": "Gemini SDK is not installed or available on this system.",
            "message": "Gemini SDK is not available. Please make sure Google GenAI is installed."
        }), 500
        
    data = request.json or {}
    message = data.get("message")
    config_data = data.get("config")
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    if not config_data:
        return jsonify({"error": "No config provided"}), 400
        
    system_prompt = """
You are a highly skilled mathematical graph layouts engineer and developer for Leerlevels, a premium educational software.
Your task is to act as an agent that modifies a mathematical diagram JSON configuration based on the user's instructions.

You must respond with a JSON block. The response MIME type must be "application/json" and you MUST output EXACTLY a JSON structure with these keys:
{
  "message": "Conversational, highly professional explanation of what you updated (in Dutch or English, matching the user's input language). Keep it encouraging and technical.",
  "config": {
     ... the entire updated configuration JSON matching the schema of the input config ...
  }
}

The diagram configuration schema supports these settings:
1. Canvas bounds:
   - `canvasWidth` (number, default 720)
   - `canvasHeight` (number, default 405)
   - `fontFamily` (string, default "Ubuntu")
2. Viewport mathematics bounds:
   - `viewport`: { xMin, xMax, yMin, yMax, marginLeft, marginRight, marginTop, marginBottom } (all numbers)
3. Grid ticks and layout settings:
   - `grid`: { show, xStep, yStep, dutchComma, showFrame, frameColor, frameWidth, boundaryStyle, xBreak, yBreak, isMultiGrid, rows, cols, gapX, gapY, cellTitles }
     - `boundaryStyle`: "box" or "arrows" (controls whether to draw a full enclosing rectangle box or traditional math x/y arrow axes)
     - `xBreak`, `yBreak`: boolean values to render zigzag scale breaks
     - `isMultiGrid`: boolean. Set to true to split the widescreen canvas into a structured grid/dashboard of independent viewports
     - `rows`, `cols`: numbers (e.g. 2, 3) representing sub-grid dimensions
     - `gapX`, `gapY`: number of physical presentation points separating cell viewports
     - `cellTitles`: object mapping cell coordinates key `"row_col"` (e.g. `"0_0"`, `"1_0"`) to string cell titles
4. Mathematical Curves / Functions:
   - `functions`: Array of function objects. Each object can be standard OR parametric.
     - Standard: { expr: "string (e.g. '0.16 * sin(pi * x)')", stroke: "color hex", strokeWidth: number, xStart: number, xEnd: number, dasharray: "none|4,4|2,2", active: bool, isParametric: false, cell: { row: number, col: number } }
     - Parametric: { xExpr: "string (e.g. 'cos(t)')", yExpr: "string (e.g. 'sin(t)')", stroke: "color hex", strokeWidth: number, tStart: number, tEnd: number, dasharray: "none|4,4|2,2", active: bool, isParametric: true, cell: { row: number, col: number } }
     - **CELL MAPPING:** When `grid.isMultiGrid` is true, you MUST map each curve to its specific panel viewport using `cell: { row: number, col: number }` (0-indexed).
5. Shading Hatch regions:
   - `hatches`: Array of { topFunc: "string", bottomFunc: "string", xStart: number, xEnd: number, stroke: "color hex", stepPt: number, active: bool }
6. Phase arrow range markers:
   - `phaseMarkers`: Array of { xStart: number, xEnd: number, yVal: number, label: "string", stroke: "color hex", active: bool }
7. Circle points highlights:
   - `points`: Array of { x: number, y: number, label: "string", dotSize: number, color: "color hex", active: bool }
8. Custom lines & arrows:
   - `lines`: Array of { x1: number, y1: number, x2: number, y2: number, stroke: "color hex", strokeWidth: number, type: "line|arrow|double_arrow", dasharray: "none|4,4|2,2", active: bool }
9. Custom text labels and LaTeX:
   - `textLabels`: Array of { text: "string (raw text or latex like '\\\\frac{dx}{dt}')", x: number, y: number, coordinateMode: "math|screen", fontSize: number, color: "color hex", align: "center|start|right", isLatex: bool, bold: bool, maskBg: bool }

Instructions:
- ONLY make changes specified or implied by the user's query.
- Keep other existing settings completely intact so the user does not lose their manual modifications or existing presets.
- If the user asks to draw parametric graphs or Lorenz systems, use the `isParametric` flag and define `xExpr` and `yExpr` with variable `t`.
- Do not add any text before or after the JSON block. Your output must be a single parsable JSON object.
"""
    
    user_prompt = f"Current diagram configuration:\n{json.dumps(config_data, indent=2)}\n\nUser instruction: {message}"
    
    try:
        # Initialize Google GenAI client
        client = genai.Client()
        
        # Call Generate Content with high thinking level
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(
                    thinking_level="high"
                )
            )
        )
        
        # Parse the JSON response
        result_text = response.text
        logger.info(f"Gemini responded: {result_text[:500]}...")
        
        result_json = json.loads(result_text)
        return jsonify(result_json)
        
    except Exception as e:
        logger.error(f"Gemini API chat call failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "message": f"AI error occurred: {str(e)}. Please check your API key in .env or try again."
        }), 500

@app.route('/api/export', methods=['POST'])
def export():
    logger.info("Received export request.")
    data = request.json or {}
    slide_data = data.get("slide_data")
    svg_content = data.get("svg", "")
    
    # Check if we should try Google Slides export
    if slide_data and GSLIDES_AVAILABLE:
        try:
            logger.info("Google Slides module available and slide data present. Attempting native export...")
            creds = get_credentials()
            if not creds:
                return jsonify({"error": "Unauthorized", "message": "Please log in with Google first"}), 401
                
            uploader = GoogleSlidesUploader(credentials=creds)
            
            # Read folder ID from request or environment
            folder_id = data.get("folder_id") or os.environ.get("DRIVE_FOLDER_ID")
            logger.info(f"Creating presentation in folder ID: {folder_id or 'Root'}")
            
            file_obj = uploader.create_presentation_from_canvas_data(
                slide_data,
                name="AI Generated Physics Diagram",
                folder_id=folder_id
            )
            
            logger.info(f"Native Slide created successfully! ID: {file_obj.get('id')}")
            return jsonify({
                "success": True,
                "url": file_obj.get("webViewLink"),
                "id": file_obj.get("id"),
                "is_slide": True
            })
            
        except Exception as e:
            logger.error(f"Google Slides API native export failed, falling back: {str(e)}")
            print(traceback.format_exc())
            
            # Offer clear feedback on what failed (e.g. API not enabled)
            err_msg = str(e)
            if "has not been used in project" in err_msg or "disabled" in err_msg:
                user_msg = "Google Slides API is not enabled in your Google Cloud Console. Please enable it to create editable Slides."
            else:
                user_msg = f"Slides export error: {err_msg}"
                
            # Fall back to a mock Google Slide URL for preview
            mock_slide_url = "https://docs.google.com/presentation/d/1v28_9H3_P9O_Q-L6kO9R53_Yg_O6q_TzR1q0npq_mock/edit?usp=sharing"
            return jsonify({
                "success": True,
                "url": mock_slide_url,
                "warning": user_msg,
                "message": f"Running in Fallback Mock mode because: {user_msg}",
                "is_slide": True
            })

    # Legacy fallback: Google Drawings via SVG-to-EMF upload (or if no slide_data was provided)
    if not svg_content:
        logger.warning("No SVG or Slide content provided for export.")
        return jsonify({"error": "No content provided"}), 400
        
    try:
        # Write SVG content to temp file
        svg_temp = "drawings/temp_upload.svg"
        emf_temp = "drawings/temp_upload.emf"
        os.makedirs("drawings", exist_ok=True)
        
        logger.info(f"Writing SVG payload to temp file: {svg_temp}")
        with open(svg_temp, "w", encoding="utf-8") as f:
            f.write(svg_content)
            
        # Convert to EMF
        if CONVERTER_AVAILABLE:
            logger.info("Starting conversion from SVG to EMF...")
            svg_to_emf(svg_temp, emf_temp)
            logger.info("SVG to EMF conversion completed successfully.")
        else:
            logger.warning("Converter not available. Skipping SVG to EMF conversion.")
        
        # Upload to Google Drive
        if GDRIVE_AVAILABLE:
            try:
                logger.info("Google Drive module available. Attempting authorization and upload...")
                creds_file = "credentials.json"
                if not os.path.exists(creds_file):
                    creds_file = "service_account.json" if os.path.exists("service_account.json") else None
                    
                logger.info(f"Using Google Drive credentials file: {creds_file}")
                uploader = GoogleDrawingsUploader(credentials_path=creds_file)
                
                folder_id = os.environ.get("DRIVE_FOLDER_ID")
                logger.info(f"Uploading file to folder ID: {folder_id or 'Root'}")
                
                file_obj = uploader.upload_vector_as_google_drawing(
                    emf_temp,
                    name="AI Generated Styled Figure",
                    folder_id=folder_id
                )
                
                logger.info(f"Drawing uploaded successfully to Google Drive. ID: {file_obj.get('id')}")
                return jsonify({
                    "success": True,
                    "url": file_obj.get("webViewLink"),
                    "id": file_obj.get("id")
                })
                
            except Exception as e:
                logger.error(f"Google Drive API upload failed, falling back to mock: {str(e)}")
                print(traceback.format_exc())
                
        # Beautiful simulated fallback if credentials or API are not configured locally yet
        mock_url = "https://docs.google.com/drawings/d/1eSvF7_ekvOWy1q0npqI8f37J9IARPBOZJte5Q3pDspw/edit?usp=sharing"
        logger.warning(f"Google Drive API or credentials not set up. Falling back to mock URL: {mock_url}")
        return jsonify({
            "success": True,
            "url": mock_url,
            "message": "Running in Development Mock mode because Google Drive API was not fully configured."
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/write_clipboard', methods=['POST'])
def write_clipboard():
    logger.info("Received request to write to system clipboard via local Python backend.")
    data = request.json or {}
    wrapped_str = data.get("wrapped")
    flat_str = data.get("flat")
    clip_id = data.get("clip_id", "2519a9aa-7fff-ab00-1255-47f90648ed96")
    fallback_text = data.get("fallback_text", "[Google Slides Graph Data]")
    
    if not wrapped_str:
        return jsonify({"success": False, "error": "No wrapped payload provided."}), 400
        
    import os
    if os.name != 'nt':
        logger.warning("Clipboard writing is only supported on Windows local development servers.")
        return jsonify({"success": False, "error": "Clipboard writing only supported on local Windows host."}), 400
        
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        # Define argument and return types for 64-bit safety
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
        
        # Build custom mime pairs
        pairs = []
        if wrapped_str:
            pairs.append(("application/x-vnd.google-docs-drawings-object+wrapped", wrapped_str))
        if clip_id:
            pairs.append(("application/x-vnd.google-docs-internal-clip-id", clip_id))
            
        # Encode the custom pairs
        raw_data = b""
        for k, v in pairs:
            raw_data += len(k).to_bytes(4, "little") + k.encode("utf-16le")
            if len(k) % 2 != 0:
                raw_data += b"\0\0"
            raw_data += len(v).to_bytes(4, "little") + v.encode("utf-16le")
            if len(v) % 2 != 0:
                raw_data += b"\0\0"
                
        total_data = len(pairs).to_bytes(4, "little") + raw_data
        raw_custom_bytes = len(total_data).to_bytes(4, "little") + total_data
        
        if not user32.OpenClipboard(None):
            logger.error("Failed to open clipboard.")
            return jsonify({"success": False, "error": "Failed to open clipboard."}), 500
            
        try:
            user32.EmptyClipboard()
            
            # Write custom format
            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw_custom_bytes))
            if h_mem:
                p_mem = kernel32.GlobalLock(h_mem)
                if p_mem:
                    ctypes.memmove(p_mem, raw_custom_bytes, len(raw_custom_bytes))
                    kernel32.GlobalUnlock(h_mem)
                    user32.SetClipboardData(CF_CHROMIUM_CUSTOM, h_mem)
                    
            # Write fallback text
            if fallback_text:
                text_bytes = (fallback_text + "\0").encode("utf-16le")
                h_text = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_bytes))
                if h_text:
                    p_text = kernel32.GlobalLock(h_text)
                    if p_text:
                        ctypes.memmove(p_text, text_bytes, len(text_bytes))
                        kernel32.GlobalUnlock(h_text)
                        user32.SetClipboardData(CF_UNICODETEXT, h_text)
                        
            logger.info("Successfully wrote custom drawing data to host clipboard via ctypes.")
            return jsonify({"success": True})
        finally:
            user32.CloseClipboard()
    except Exception as e:
        logger.error(f"Failed to write to clipboard via ctypes: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
