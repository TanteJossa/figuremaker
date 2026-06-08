import os
import sys
import json
import uuid
import re
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Define Scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

def authenticate(force_oauth=False):
    """
    Handles authentication and returns both the credentials and the Drive API service.
    """
    creds = None
    
    # Check if service_account.json exists and we are not forcing OAuth
    service_account_path = "service_account.json"
    if os.path.exists(service_account_path) and not force_oauth:
        print(f"Authenticating using Service Account: {service_account_path}")
        try:
            creds = service_account.Credentials.from_service_account_file(
                service_account_path, scopes=SCOPES
            )
            drive_service = build('drive', 'v3', credentials=creds)
            return creds, drive_service
        except Exception as e:
            print(f"Service account authentication failed, trying OAuth: {e}")

    # OAuth User Flow fallback
    token_path = "token.json"
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            print("Loaded existing user OAuth credentials from token.json")
        except Exception as e:
            print(f"Failed to load existing token: {e}")
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired user credentials...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Failed to refresh credentials: {e}")
                creds = None
                
        if not creds:
            oauth_client_secret = "credentials.json"
            if not os.path.exists(oauth_client_secret):
                raise FileNotFoundError(
                    f"To use User OAuth, please download 'credentials.json' (OAuth Client ID) "
                    f"from Google Cloud Console and place it in the project root."
                )
            print("Initiating local browser-based authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(oauth_client_secret, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
    drive_service = build('drive', 'v3', credentials=creds)
    return creds, drive_service

def get_access_token(creds):
    """
    Ensures the credentials token is valid and returns it.
    """
    if not creds.valid:
        creds.refresh(Request())
    return creds.token

def extract_tokens_from_html(html_content):
    """
    Uses regex to extract the CSRF token and revision from Google Drawings HTML.
    """
    # Look for the CSRF token in the HTML
    token_match = re.search(r'([A-Za-z0-9_-]+:1[0-9]{12})', html_content)
    token = token_match.group(1) if token_match else None
    
    # Look for revision number
    rev_match = re.search(r'"revision"\s*:\s*([0-9]+)', html_content)
    if not rev_match:
        rev_match = re.search(r'"rev"\s*:\s*([0-9]+)', html_content)
    
    rev = int(rev_match.group(1)) if rev_match else 1
    
    return token, rev

def fetch_fresh_revision_and_token(drawing_id, cookies_str=None, access_token=None):
    """
    Fetches the drawing edit page to get the absolute up-to-date revision and token.
    """
    edit_url = f"https://docs.google.com/drawings/d/{drawing_id}/edit"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    }
    if cookies_str:
        headers["Cookie"] = cookies_str
    elif access_token:
        headers["Authorization"] = f"Bearer {access_token}"
        
    response = requests.get(edit_url, headers=headers)
    if response.status_code == 200:
        return extract_tokens_from_html(response.text)
    return None, 1

def execute_save_request(drawing_id, csrf_token, rev, req_id, sid, commands, cookies_str=None, access_token=None, referer_url=None, retry_count=0):
    """
    Sends a save request to Google Drawings with the given revision, request ID, session ID, and commands.
    Supports auto-recovery and retrying if a revision mismatch (HTTP 550) occurs.
    """
    bundle = {
        "commands": commands,
        "sid": sid,
        "reqId": req_id
    }
    
    bundles_json = json.dumps([bundle])
    payload = {
        "rev": rev,
        "bundles": bundles_json
    }
    
    save_url = (
        f"https://docs.google.com/drawings/u/0/d/{drawing_id}/save"
        f"?id={drawing_id}"
        f"&sid={sid}"
        f"&vc=1"
        f"&c=1"
        f"&w=1"
        f"&flr=0"
        f"&smv=9"
        f"&smb=%5B9%2C+%5D"
        f"&token={csrf_token}"
        f"&includes_info_params=1"
        f"&usp=drive_web"
        f"&cros_files=false"
        f"&nded=false"
    )
    
    save_headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-Same-Domain": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Referer": referer_url or f"https://docs.google.com/drawings/d/{drawing_id}/edit",
        "Origin": "https://docs.google.com",
    }
    
    if cookies_str:
        save_headers["Cookie"] = cookies_str
    elif access_token:
        save_headers["Authorization"] = f"Bearer {access_token}"
        
    response = requests.post(save_url, data=payload, headers=save_headers)
    
    # Handle revision mismatch auto-recovery (HTTP 550) with a max retry limit
    if response.status_code == 550 and retry_count < 2:
        print(f"  [Auto-Recovery] Revision mismatch (sent {rev}). Fetching a completely fresh revision from edit page...")
        fresh_token, fresh_rev = fetch_fresh_revision_and_token(drawing_id, cookies_str=cookies_str, access_token=access_token)
        if fresh_token:
            csrf_token = fresh_token
        print(f"  [Auto-Recovery] Retrying with fresh revision {fresh_rev}...")
        return execute_save_request(
            drawing_id=drawing_id,
            csrf_token=csrf_token,
            rev=fresh_rev,
            req_id=req_id,
            sid=sid,
            commands=commands,
            cookies_str=cookies_str,
            access_token=access_token,
            referer_url=referer_url,
            retry_count=retry_count + 1
        )
            
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}: {response.text}"
        
    # Parse next revision number from response
    response_text = response.text
    clean_json_str = response_text.lstrip(")]}'\n")
    try:
        data = json.loads(clean_json_str)
        if "revisionRanges" in data and len(data["revisionRanges"]) > 0:
            new_rev = data["revisionRanges"][0][1]
            return new_rev, response_text
    except Exception as e:
        pass
        
    return rev + 1, response_text

def create_blank_drawing(drive_service, folder_id=None):
    """
    Creates a new blank Google Drawing document in the specified folder.
    """
    file_metadata = {
        'name': 'API Text & Arrows Test Drawing',
        'mimeType': 'application/vnd.google-apps.drawing'
    }
    if folder_id:
        file_metadata['parents'] = [folder_id]
        
    print("Creating a new blank Google Drawing in Google Drive...")
    file_obj = drive_service.files().create(
        body=file_metadata,
        fields='id, name, webViewLink'
    ).execute()
    
    print(f"Created Drawing successfully! ID: {file_obj.get('id')}")
    print(f"Web View Link: {file_obj.get('webViewLink')}")
    return file_obj

def add_text_and_arrows_via_api(drawing_id, access_token=None, cookies_str=None):
    """
    Uses the undocumented Google Drawings API to add a text box and an arrow line sequentially.
    """
    # 1. Fetch the Google Drawings edit page to obtain the CSRF token and revision
    edit_url = f"https://docs.google.com/drawings/d/{drawing_id}/edit"
    print(f"\nFetching Drawings edit page to retrieve session/CSRF tokens: {edit_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    }
    
    if cookies_str:
        headers["Cookie"] = cookies_str
        print("Using Browser cookies from GOOGLE_COOKIES for request authentication.")
    elif access_token:
        headers["Authorization"] = f"Bearer {access_token}"
        print("Using Google API OAuth access token for request authentication.")
    else:
        print("Error: Neither OAuth access token nor browser cookies were provided.")
        return False
        
    response = requests.get(edit_url, headers=headers)
    if response.status_code != 200:
        print(f"Error: Failed to fetch edit page. HTTP Status Code: {response.status_code}")
        print(response.text[:1000])
        return False
        
    html_content = response.text
    csrf_token, current_rev = extract_tokens_from_html(html_content)
    
    if not csrf_token:
        token_match = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', html_content)
        if token_match:
            csrf_token = token_match.group(1)
            
    if not csrf_token:
        print("Warning: Could not extract CSRF edit token from HTML.")
        return False
        
    print(f"Successfully extracted CSRF Token: {csrf_token}")
    print(f"Starting Document Base Revision: {current_rev}")
    
    sid = uuid.uuid4().hex[:16]
    print(f"Generated Session ID (sid): {sid}")
    
    # Generate Unique Shape IDs
    elem_prefix = f"g{uuid.uuid4().hex[:10]}"
    text_box_id = f"{elem_prefix}_0_0"
    arrow_line_id = f"{elem_prefix}_0_1"
    
    # === STEP 1: CREATE TEXTBOX SHAPE ===
    insert_textbox = [
        3, 
        text_box_id, 
        153, 
        [1.8092, 0, 0, 1.0554, 50000, 50000], 
        [
            14, 0, 
            15, "#CFE2F3",  # Fill Color (Light Blue)
            19, "#000000",  # Stroke Color (Black)
            22, 381, 
            27, 1.3, 
            30, 1.3, 
            51, ["", 0], 
            52, ["", 0]
        ], 
        "p"
    ]
    print(f"\n[Step 1/3] Creating Textbox Shape '{text_box_id}'...")
    next_rev, err_msg = execute_save_request(
        drawing_id=drawing_id,
        csrf_token=csrf_token,
        rev=current_rev,
        req_id=0,
        sid=sid,
        commands=[insert_textbox],
        cookies_str=cookies_str,
        access_token=access_token,
        referer_url=edit_url
    )
    
    if not next_rev:
        print(f"Failed on Step 1: Create Textbox. Message: {err_msg}")
        return False
        
    print(f"Step 1 Success! New Revision: {next_rev}")
    
    # === STEP 2: ATOMICALLY INITIALIZE AND SET TEXT CONTENT ===
    text_content = "Hello, Google Drawings!"
    initialize_text_story = [16, text_box_id, None, 0, len(text_content)]
    insert_text_value = [15, text_box_id, None, 0, text_content]
    atomic_text_group = [
        4,
        [
            initialize_text_story,
            insert_text_value
        ]
    ]
    
    print(f"\n[Step 2/3] Adding Text Content to Textbox '{text_box_id}' (initializing story & inserting text)...")
    next_rev, err_msg2 = execute_save_request(
        drawing_id=drawing_id,
        csrf_token=csrf_token,
        rev=next_rev,
        req_id=1,
        sid=sid,
        commands=[atomic_text_group],
        cookies_str=cookies_str,
        access_token=access_token,
        referer_url=edit_url
    )
    
    if not next_rev:
        print(f"Failed on Step 2: Set Text. Message: {err_msg2}")
        return False
        
    print(f"Step 2 Success! New Revision: {next_rev}")
    
    # === STEP 3: CREATE ARROW LINE ===
    insert_arrow = [
        4, 
        [
            [
                3, 
                arrow_line_id, 
                108, 
                [1.7074, 0, 0, 0.2738, 250000, 100000], 
                [
                    165, 2, 
                    166, 1, 
                    44, 0, 
                    45, 1
                ]
            ], 
            "p"
        ]
    ]
    update_arrow_transform = [
        6, 
        arrow_line_id, 
        [1.7074, 0, 0, 0.1334, 250000, 100000]
    ]
    
    print(f"\n[Step 3/3] Creating Styled Arrow Connection Line '{arrow_line_id}'...")
    final_rev, err_msg3 = execute_save_request(
        drawing_id=drawing_id,
        csrf_token=csrf_token,
        rev=next_rev,
        req_id=2, 
        sid=sid,
        commands=[insert_arrow, update_arrow_transform],
        cookies_str=cookies_str,
        access_token=access_token,
        referer_url=edit_url
    )
    
    if not final_rev:
        print(f"Failed on Step 3: Create Arrow Line. Message: {err_msg3}")
        return False
        
    print(f"Step 3 Success! Final Document Revision: {final_rev}")
    return True

def main():
    load_dotenv()
    force_oauth = "--oauth" in sys.argv
    drawing_id = None
    
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            drawing_id = arg
            break
            
    cookies_str = os.environ.get("GOOGLE_COOKIES")
    access_token = None
    drive_service = None
    
    # If forcing OAuth, IGNORE GOOGLE_COOKIES completely!
    if force_oauth:
        cookies_str = None
        print("OAuth flow forced: Ignoring GOOGLE_COOKIES.")
        
    # 1. Authenticate with Google Drive (if cookies not available or specifically requested)
    if not cookies_str or force_oauth or not drawing_id:
        try:
            creds, drive_service = authenticate(force_oauth=force_oauth)
            access_token = get_access_token(creds)
        except Exception as e:
            print(f"Google Drive Authentication failed: {e}")
            if not cookies_str:
                sys.exit(1)
                
    if not drawing_id:
        folder_id = os.environ.get("DRIVE_FOLDER_ID")
        try:
            drawing_obj = create_blank_drawing(drive_service, folder_id)
            drawing_id = drawing_obj['id']
        except Exception as e:
            print(f"Failed to create drawing: {e}")
            sys.exit(1)
            
    print(f"\nModifying drawing '{drawing_id}' using the undocumented save API...")
    success = add_text_and_arrows_via_api(drawing_id, access_token=access_token, cookies_str=cookies_str)
    
    if success:
        print("\n" + "="*50)
        print("Please visit the following URL to verify that the text and arrow line are natively rendered and fully editable:")
        print(f"https://docs.google.com/drawings/d/{drawing_id}/edit")
        print("="*50 + "\n")
    else:
        print("\nOperation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
