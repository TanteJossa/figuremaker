import os
import json
from gslides_uploader import GoogleSlidesUploader

def test_slides():
    print("Starting Google Slides API uploader test...")
    canvas_data = {
        "width": 1000,
        "height": 562.5,
        "font_family": "Ubuntu",
        "elements": [
            {
                "type": "rect",
                "x": 100,
                "y": 100,
                "width": 400,
                "height": 200,
                "fill": "#cfe2f3",
                "stroke": "#0b5394",
                "stroke_width": 3.0
            },
            {
                "type": "text",
                "x": 120,
                "y": 150,
                "width": 360,
                "height": 100,
                "text": "Hello, Google Slides!",
                "font_size": 24,
                "bold": True,
                "color": "#000000",
                "align": "center"
            }
        ]
    }
    
    creds_file = "credentials.json"
    if not os.path.exists(creds_file):
        creds_file = "service_account.json" if os.path.exists("service_account.json") else None
        
    print(f"Using credentials from: {creds_file}")
    uploader = GoogleSlidesUploader(credentials_path=creds_file)
    file_obj = uploader.create_presentation_from_canvas_data(
        canvas_data,
        name="Deterministic Google Slides Graph Test",
        folder_id=os.environ.get("DRIVE_FOLDER_ID")
    )
    print(f"Success! Google Slides presentation created.")
    print(f"URL: {file_obj.get('webViewLink')}")

if __name__ == "__main__":
    test_slides()
