import os
import sys
from leerlevels_style import Canvas, COLORS, draw_header, draw_rect, draw_line
from converter import svg_to_emf
from gdrive_uploader import GoogleDrawingsUploader
from dotenv import load_dotenv

load_dotenv()

def test_pipeline():
    print("--- STARTING END-TO-END PIPELINE TEST ---")
    
    # 1. Generate test SVG
    svg_path = "drawings/test_pipeline.svg"
    emf_path = "drawings/test_pipeline.emf"
    os.makedirs("drawings", exist_ok=True)
    
    print(f"1. Generating test SVG at: {svg_path}")
    canvas = Canvas(width=1000, height=562.5)
    draw_header(canvas, "End-to-End Pipeline Test")
    canvas.add(draw_rect(x=100, y=150, width=800, height=300, fill=COLORS['yellow_bg'], stroke=COLORS['yellow_primary'], stroke_width=3.0, rx=8, ry=8))
    canvas.add(draw_line(x1=200, y1=200, x2=800, y2=400, stroke=COLORS['black'], stroke_width=4.0))
    canvas.save(svg_path)
    print("Test SVG generated successfully.")
    
    # 2. Convert to EMF
    print(f"2. Converting SVG to EMF: {svg_path} -> {emf_path}")
    try:
        svg_to_emf(svg_path, emf_path)
    except Exception as e:
        print(f"Conversion failed (using simulation/fallback if converter not installed): {e}")
        
    # 3. Upload to Google Drive using credentials.json or service_account.json
    creds_file = "credentials.json"
    if not os.path.exists(creds_file):
        creds_file = "service_account.json"
        
    if not os.path.exists(creds_file):
        print(f"Error: Neither credentials.json nor service_account.json was found. Cannot proceed with upload.")
        return
        
    print(f"3. Authenticating and uploading to Google Drive using credentials: {creds_file}")
    try:
        uploader = GoogleDrawingsUploader(credentials_path=creds_file)
        folder_id = os.environ.get("DRIVE_FOLDER_ID")
        print(f"Uploading to Drive Folder ID: {folder_id or 'Root'}")
        
        file_obj = uploader.upload_vector_as_google_drawing(
            emf_path,
            name="AI Pipeline End-to-End Test",
            folder_id=folder_id
        )
        print("\n--- PIPELINE TEST SUCCEEDED! ---")
        print(f"New Google Drawings URL: {file_obj.get('webViewLink')}")
        print(f"New File ID: {file_obj.get('id')}")
        
    except Exception as e:
        print(f"\n--- PIPELINE TEST FAILED ---")
        print(f"Error details: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_pipeline()
