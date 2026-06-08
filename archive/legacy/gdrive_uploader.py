import os
import sys

# We check imports and provide clear instructions if libraries are missing.
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False

# Define OAuth scopes needed to create files in Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDrawingsUploader:
    def __init__(self, credentials_path=None, token_path="token.json"):
        """
        Initializes the Google Drive API connection.
        Supports both Service Account JSON and User OAuth Flow (Installed App Flow).
        """
        if not API_AVAILABLE:
            msg = (
                "Google API Client libraries are missing.\n"
                "Please install them using:\n"
                "   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )
            raise ImportError(msg)
            
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()
        
    def _authenticate(self):
        """
        Handles authentication and returns the Drive API service.
        """
        creds = None
        
        # Scenario A: Service Account (Ideal for Server Backend / APIs)
        if self.credentials_path and os.path.exists(self.credentials_path):
            print(f"Authenticating using Service Account: {self.credentials_path}")
            try:
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_path, scopes=SCOPES
                )
                return build('drive', 'v3', credentials=creds)
            except Exception as e:
                print(f"Service account authentication failed, falling back to OAuth flow: {e}")
                
        # Scenario B: OAuth 2.0 User Consent (Ideal for local testing & personal user drives)
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path or not os.path.exists(self.credentials_path):
                    # We look for a default credentials file name
                    oauth_client_secret = "credentials.json"
                    if not os.path.exists(oauth_client_secret):
                        raise FileNotFoundError(
                            f"To use User OAuth, please download 'credentials.json' (OAuth Client ID) "
                            f"from Google Cloud Console and place it in the project root."
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(oauth_client_secret, SCOPES)
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                # Use port 0 for random ports (perfectly supported on Desktop Apps)
                creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
                
        return build('drive', 'v3', credentials=creds)

    def upload_vector_as_google_drawing(self, filepath, name=None, folder_id=None):
        """
        Uploads an EMF vector graphic to Google Drive and converts it into a native,
        fully editable Google Drawings document.
        
        :param filepath: Path to the local .emf file.
        :param name: Target file name in Google Drive (defaults to original filename).
        :param folder_id: Optional ID of the parent folder in Google Drive.
        :return: Dict containing the file ID and webViewLink (URL to open in browser).
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
            
        if name is None:
            name = os.path.splitext(os.path.basename(filepath))[0]
            
        print(f"Uploading and converting '{filepath}' to Google Drawings as '{name}'...")
        
        # Metadata required to convert the vector graphic to a Google Drawings file on upload:
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.drawing' # Crucial: tells Drive to convert to Google Drawings
        }
        
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        # EMF MIME Type is application/x-msmetafile
        media = MediaFileUpload(
            filepath,
            mimetype='application/x-msmetafile',
            resumable=True
        )
        
        try:
            file_obj = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            print(f"Upload successful!")
            print(f"File Name: {file_obj.get('name')}")
            print(f"File ID: {file_obj.get('id')}")
            print(f"Google Drawings Link: {file_obj.get('webViewLink')}")
            return file_obj
            
        except Exception as e:
            print(f"Error during Google Drawings conversion/upload: {e}")
            raise e

if __name__ == "__main__":
    if not API_AVAILABLE:
        print("Google API Client libraries are not installed.")
        print("Please install them with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        sys.exit(1)
        
    if len(sys.argv) < 2:
        print("Usage: python gdrive_uploader.py <path_to_emf_file> [target_name] [google_drive_folder_id]")
        sys.exit(1)
        
    emf_file = sys.argv[1]
    target_name = sys.argv[2] if len(sys.argv) > 2 else None
    folder_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Attempt OAuth client login
    try:
        uploader = GoogleDrawingsUploader()
        uploader.upload_vector_as_google_drawing(emf_file, name=target_name, folder_id=folder_id)
    except Exception as e:
        print(f"\nUploader failed: {e}")
        print("\nNote: For this script to run, you need valid Google API Credentials ('credentials.json') in the project folder.")
