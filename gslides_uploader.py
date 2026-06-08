import os
import sys
import json
import traceback

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

# We need both Drive and Slides scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/presentations'
]

# Leerlevels standard colors for backup/defaulting
COLORS = {
    'black': '#000000',
    'dark_gray': '#666666',
    'mid_gray': '#b7b7b7',
    'light_gray': '#cccccc',
    'bg_gray': '#efefef',
    'white': '#ffffff',
    
    'red_primary': '#980000',
    'red_bg': '#e6b8af',
    
    'blue_primary': '#0b5394',
    'blue_bg': '#cfe2f3',
    
    'green_primary': '#38761d',
    'green_bg': '#d9ead3',
    'yellow_primary': '#bf9000',
    'yellow_bg': '#fff2cc'
}

def hex_to_slides_color(hex_str):
    if not hex_str or hex_str == 'none':
        return {'rgbColor': {'red': 0, 'green': 0, 'blue': 0}}
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = "".join([c*2 for c in hex_str])
    if len(hex_str) == 6:
        try:
            r = int(hex_str[0:2], 16) / 255.0
            g = int(hex_str[2:4], 16) / 255.0
            b = int(hex_str[4:6], 16) / 255.0
            return {
                'rgbColor': {
                    'red': r,
                    'green': g,
                    'blue': b
                }
            }
        except ValueError:
            pass
    return {'rgbColor': {'red': 0, 'green': 0, 'blue': 0}}

def svg_dasharray_to_slides(dasharray):
    if not dasharray or dasharray == 'none':
        return 'SOLID'
    # Map any common dash values to DASH
    return 'DASH'

class GoogleSlidesUploader:
    def __init__(self, credentials_path=None, token_path="token.json", credentials=None):
        if not API_AVAILABLE:
            msg = (
                "Google API Client libraries are missing.\n"
                "Please install them using:\n"
                "   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )
            raise ImportError(msg)
            
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.credentials = credentials
        self.slides_service, self.drive_service = self._authenticate()
        
    def _authenticate(self):
        if self.credentials:
            return build('slides', 'v1', credentials=self.credentials), build('drive', 'v3', credentials=self.credentials)
            
        creds = None
        
        # Scenario A: Service Account
        if self.credentials_path and os.path.exists(self.credentials_path):
            # Check if it is a service account JSON or OAuth client secrets JSON
            try:
                with open(self.credentials_path, 'r') as f:
                    data = json.load(f)
                if data.get('type') == 'service_account':
                    print(f"[Slides Uploader] Authenticating using Service Account: {self.credentials_path}")
                    creds = service_account.Credentials.from_service_account_file(
                        self.credentials_path, scopes=SCOPES
                    )
                    return build('slides', 'v1', credentials=creds), build('drive', 'v3', credentials=creds)
            except Exception as e:
                print(f"[Slides Uploader] Service account check failed, falling back to OAuth: {e}")
                
        # Scenario B: OAuth 2.0 User Consent
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                print(f"[Slides Uploader] Error loading token.json: {e}")
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"[Slides Uploader] Refresh token expired or invalid, re-authenticating: {e}")
                    creds = None
            
            if not creds:
                oauth_client_secret = self.credentials_path or "credentials.json"
                if not os.path.exists(oauth_client_secret):
                    raise FileNotFoundError(
                        f"To authenticate, please download your 'credentials.json' (OAuth Client ID) "
                        f"from Google Cloud Console and place it in the project root."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(oauth_client_secret, SCOPES)
                creds = flow.run_local_server(port=0)
                
            # Save the credentials for next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
                
        return build('slides', 'v1', credentials=creds), build('drive', 'v3', credentials=creds)

    def create_presentation_from_canvas_data(self, canvas_data, name="AI Generated Styled Presentation", folder_id=None):
        """
        Creates a new 1-page Google Slide presentation and populates it with native,
        fully editable text boxes, lines, and shapes based on the canvas JSON payload.
        """
        width = canvas_data.get("width", 1000)
        height = canvas_data.get("height", 562.5)
        font_family = canvas_data.get("font_family", "Ubuntu")
        elements = canvas_data.get("elements", [])
        
        print(f"[Slides Uploader] Creating 1-page presentation '{name}' with size {width}x{height} PT...")
        
        # 1. Create the blank presentation with custom size
        presentation_body = {
            'title': name,
            'pageSize': {
                'width': {'magnitude': width, 'unit': 'PT'},
                'height': {'magnitude': height, 'unit': 'PT'}
            }
        }
        
        presentation = self.slides_service.presentations().create(body=presentation_body).execute()
        presentation_id = presentation.get('presentationId')
        
        # Google Slides creates a default presentation with a title slide containing placeholder shapes.
        # Let's retrieve the first slide and delete any default layout/placeholder shapes so we have a clean canvas!
        slides = presentation.get('slides', [])
        if not slides:
            raise RuntimeError("Failed to retrieve slides from the newly created presentation.")
            
        page_id = slides[0].get('objectId')
        page_elements = slides[0].get('pageElements', [])
        
        # Collect delete requests for any default title/subtitle placeholder shapes
        delete_requests = []
        for pe in page_elements:
            delete_requests.append({
                'deleteObject': {
                    'objectId': pe.get('objectId')
                }
            })
            
        if delete_requests:
            self.slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': delete_requests}
            ).execute()
            print(f"[Slides Uploader] Cleaned {len(delete_requests)} default placeholder elements from Slide 1.")
            
        # 2. Translate elements to Slides API batchUpdate requests
        requests = []
        drive_files_to_cleanup = []
        
        for idx, el in enumerate(elements):
            el_type = el.get("type")
            object_id = el.get("id") or el.get("objectId") or f"element_{idx}_{el_type}"
            
            if el_type == "rect":
                # Create Rectangle shape
                requests.append({
                    'createShape': {
                        'objectId': object_id,
                        'shapeType': 'RECTANGLE',
                        'elementProperties': {
                            'pageObjectId': page_id,
                            'size': {
                                'width': {'magnitude': el.get("width", 100), 'unit': 'PT'},
                                'height': {'magnitude': el.get("height", 100), 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1, 'scaleY': 1,
                                'translateX': el.get("x", 0), 'translateY': el.get("y", 0),
                                'unit': 'PT'
                            }
                        }
                    }
                })
                
                # Apply outline and fill
                fill = el.get("fill", "none")
                stroke = el.get("stroke", COLORS['black'])
                stroke_width = el.get("stroke_width", 2.0)
                dasharray = el.get("dasharray", "none")
                
                shape_props = {}
                if fill != "none":
                    shape_props['shapeBackgroundFill'] = {
                        'solidFill': {
                            'color': hex_to_slides_color(fill)
                        }
                    }
                else:
                    shape_props['shapeBackgroundFill'] = {
                        'propertyState': 'NOT_RENDERED'
                    }
                    
                if stroke != "none":
                    shape_props['outline'] = {
                        'outlineFill': {
                            'solidFill': {
                                'color': hex_to_slides_color(stroke)
                            }
                        },
                        'weight': {
                            'magnitude': stroke_width,
                            'unit': 'PT'
                        },
                        'dashStyle': svg_dasharray_to_slides(dasharray)
                    }
                else:
                    shape_props['outline'] = {
                        'propertyState': 'NOT_RENDERED'
                    }
                
                requests.append({
                    'updateShapeProperties': {
                        'objectId': object_id,
                        'shapeProperties': shape_props,
                        'fields': 'shapeBackgroundFill,outline'
                    }
                })
                
            elif el_type in ["ellipse", "circle"]:
                # Create Ellipse shape
                requests.append({
                    'createShape': {
                        'objectId': object_id,
                        'shapeType': 'ELLIPSE',
                        'elementProperties': {
                            'pageObjectId': page_id,
                            'size': {
                                'width': {'magnitude': el.get("width", 100), 'unit': 'PT'},
                                'height': {'magnitude': el.get("height", 100), 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1, 'scaleY': 1,
                                'translateX': el.get("x", 0), 'translateY': el.get("y", 0),
                                'unit': 'PT'
                            }
                        }
                    }
                })
                
                # Apply outline and fill
                fill = el.get("fill", "none")
                stroke = el.get("stroke", COLORS['black'])
                stroke_width = el.get("stroke_width", 2.0)
                dasharray = el.get("dasharray", "none")
                
                shape_props = {}
                if fill != "none":
                    shape_props['shapeBackgroundFill'] = {
                        'solidFill': {
                            'color': hex_to_slides_color(fill)
                        }
                    }
                else:
                    shape_props['shapeBackgroundFill'] = {
                        'propertyState': 'NOT_RENDERED'
                    }
                    
                if stroke != "none":
                    shape_props['outline'] = {
                        'outlineFill': {
                            'solidFill': {
                                'color': hex_to_slides_color(stroke)
                            }
                        },
                        'weight': {
                            'magnitude': stroke_width,
                            'unit': 'PT'
                        },
                        'dashStyle': svg_dasharray_to_slides(dasharray)
                    }
                else:
                    shape_props['outline'] = {
                        'propertyState': 'NOT_RENDERED'
                    }
                
                requests.append({
                    'updateShapeProperties': {
                        'objectId': object_id,
                        'shapeProperties': shape_props,
                        'fields': 'shapeBackgroundFill,outline'
                    }
                })
                
            elif el_type == "line":
                x1, y1 = el.get("x1", 0), el.get("y1", 0)
                x2, y2 = el.get("x2", 0), el.get("y2", 0)
                dx, dy = x2 - x1, y2 - y1
                w, h = abs(dx), abs(dy)
                if w == 0: w = 0.1
                if h == 0: h = 0.1
                
                scale_x = 1.0 if dx >= 0 else -1.0
                scale_y = 1.0 if dy >= 0 else -1.0
                
                requests.append({
                    'createLine': {
                        'objectId': object_id,
                        'lineCategory': 'STRAIGHT',
                        'elementProperties': {
                            'pageObjectId': page_id,
                            'size': {
                                'width': {'magnitude': w, 'unit': 'PT'},
                                'height': {'magnitude': h, 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': scale_x, 'scaleY': scale_y,
                                'translateX': x1, 'translateY': y1,
                                'unit': 'PT'
                            }
                        }
                    }
                })
                
                stroke = el.get("stroke", COLORS['black'])
                stroke_width = el.get("stroke_width", 2.0)
                dasharray = el.get("dasharray", "none")
                
                requests.append({
                    'updateLineProperties': {
                        'objectId': object_id,
                        'lineProperties': {
                            'lineFill': {
                                'solidFill': {
                                    'color': hex_to_slides_color(stroke)
                                }
                            },
                            'weight': {
                                'magnitude': stroke_width,
                                'unit': 'PT'
                            },
                            'dashStyle': svg_dasharray_to_slides(dasharray)
                        },
                        'fields': 'lineFill,weight,dashStyle'
                    }
                })
                
            elif el_type == "arrow":
                x1, y1 = el.get("x1", 0), el.get("y1", 0)
                x2, y2 = el.get("x2", 0), el.get("y2", 0)
                dx, dy = x2 - x1, y2 - y1
                w, h = abs(dx), abs(dy)
                if w == 0: w = 0.1
                if h == 0: h = 0.1
                
                scale_x = 1.0 if dx >= 0 else -1.0
                scale_y = 1.0 if dy >= 0 else -1.0
                
                requests.append({
                    'createLine': {
                        'objectId': object_id,
                        'lineCategory': 'STRAIGHT',
                        'elementProperties': {
                            'pageObjectId': page_id,
                            'size': {
                                'width': {'magnitude': w, 'unit': 'PT'},
                                'height': {'magnitude': h, 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': scale_x, 'scaleY': scale_y,
                                'translateX': x1, 'translateY': y1,
                                'unit': 'PT'
                            }
                        }
                    }
                })
                
                stroke = el.get("stroke", COLORS['black'])
                stroke_width = el.get("stroke_width", 3.0)
                
                requests.append({
                    'updateLineProperties': {
                        'objectId': object_id,
                        'lineProperties': {
                            'lineFill': {
                                'solidFill': {
                                    'color': hex_to_slides_color(stroke)
                                }
                            },
                            'weight': {
                                'magnitude': stroke_width,
                                'unit': 'PT'
                            },
                            'endArrow': 'STEALTH_ARROW'
                        },
                        'fields': 'lineFill,weight,endArrow'
                    }
                })
                
            elif el_type == "text":
                x = el.get("x", 0)
                y = el.get("y", 0)
                text = el.get("text", "")
                font_sz = el.get("font_size", 16)
                color = el.get("color", COLORS['black'])
                bold = el.get("bold", False)
                italic = el.get("italic", False)
                align = el.get("align", "start")
                mask_bg = el.get("mask_bg", False)
                is_latex = el.get("is_latex", False) or el.get("isLatex", False) or (text.startswith("\\") and len(text) > 1)
                
                if is_latex:
                    try:
                        from graph_engine import compile_latex_to_png
                        latex_meta = compile_latex_to_png(text, font_sz, color, align, group_id=object_id)
                        if latex_meta:
                            local_path = latex_meta['local_path']
                            w_slide = latex_meta['width']
                            h_slide = latex_meta['height']
                            tx = x + latex_meta['x_offset']
                            ty = y + latex_meta['y_offset']
                            
                            print(f"[Slides Uploader] Uploading temporary LaTeX text image to Google Drive: {local_path}")
                            media = MediaFileUpload(local_path, mimetype='image/png')
                            drive_file = self.drive_service.files().create(
                                body={
                                    'name': os.path.basename(local_path),
                                    'parents': [folder_id] if folder_id else []
                                },
                                media_body=media,
                                fields='id, webContentLink'
                            ).execute()
                            
                            file_id = drive_file.get('id')
                            drive_files_to_cleanup.append(file_id)
                            
                            self.drive_service.permissions().create(
                                fileId=file_id,
                                body={'role': 'reader', 'type': 'anyone'}
                            ).execute()
                            
                            file_metadata = self.drive_service.files().get(
                                fileId=file_id,
                                fields='webContentLink'
                            ).execute()
                            url = file_metadata.get('webContentLink')
                            
                            if url:
                                if mask_bg:
                                    bg_id = f"{object_id}_bg"
                                    requests.append({
                                        'createShape': {
                                            'objectId': bg_id,
                                            'shapeType': 'RECTANGLE',
                                            'elementProperties': {
                                                'pageObjectId': page_id,
                                                'size': {
                                                    'width': {'magnitude': w_slide, 'unit': 'PT'},
                                                    'height': {'magnitude': h_slide, 'unit': 'PT'}
                                                },
                                                'transform': {
                                                    'scaleX': 1, 'scaleY': 1,
                                                    'translateX': tx, 'translateY': ty,
                                                    'unit': 'PT'
                                                }
                                            }
                                        }
                                    })
                                    requests.append({
                                        'updateShapeProperties': {
                                            'objectId': bg_id,
                                            'shapeProperties': {
                                                'shapeBackgroundFill': {
                                                    'solidFill': {
                                                        'color': hex_to_slides_color(COLORS['white'])
                                                    }
                                                },
                                                'outline': {
                                                    'propertyState': 'NOT_RENDERED'
                                                }
                                            },
                                            'fields': 'shapeBackgroundFill,outline'
                                        }
                                    })
                                requests.append({
                                    'createImage': {
                                        'objectId': object_id,
                                        'url': url,
                                        'elementProperties': {
                                            'pageObjectId': page_id,
                                            'size': {
                                                'width': {'magnitude': w_slide, 'unit': 'PT'},
                                                'height': {'magnitude': h_slide, 'unit': 'PT'}
                                            },
                                            'transform': {
                                                'scaleX': 1, 'scaleY': 1,
                                                'translateX': tx, 'translateY': ty,
                                                'unit': 'PT'
                                            }
                                        }
                                    }
                                })
                                continue  # Process next element
                    except Exception as latex_err:
                        print(f"[Slides Uploader] Error rendering/uploading LaTeX text element '{object_id}': {latex_err}")
                        # Fallback to normal text box rendering below

                # Setup generous bounding box so math fonts and labels fit beautifully
                box_w = el.get("width", 400)
                box_h = el.get("height", font_sz * 2.5 if font_sz * 2.5 > 40 else 40)
                
                # Offset so text aligns correctly relative to anchor (x, y)
                if align == "center":
                    tx = x - (box_w / 2.0)
                elif align == "right":
                    tx = x - box_w
                else:
                    tx = x
                    
                # Offset y slightly so text box middle matches baseline
                ty = y - (box_h / 2.0)
                
                requests.append({
                    'createShape': {
                        'objectId': object_id,
                        'shapeType': 'TEXT_BOX',
                        'elementProperties': {
                            'pageObjectId': page_id,
                            'size': {
                                'width': {'magnitude': box_w, 'unit': 'PT'},
                                'height': {'magnitude': box_h, 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1, 'scaleY': 1,
                                'translateX': tx, 'translateY': ty,
                                'unit': 'PT'
                            }
                        }
                    }
                })
                
                # Insert text
                requests.append({
                    'insertText': {
                        'objectId': object_id,
                        'insertionIndex': 0,
                        'text': text
                    }
                })
                
                # Style text
                requests.append({
                    'updateTextStyle': {
                        'objectId': object_id,
                        'textRange': {'type': 'ALL'},
                        'style': {
                            'bold': bold,
                            'italic': italic,
                            'fontSize': {'magnitude': font_sz, 'unit': 'PT'},
                            'foregroundColor': {
                                'opaqueColor': hex_to_slides_color(color)
                            },
                            'fontFamily': font_family
                        },
                        'fields': 'bold,italic,fontSize,foregroundColor,fontFamily'
                    }
                })
                
                # Align paragraph
                p_align = 'CENTER' if align == 'center' else ('END' if align == 'right' else 'START')
                requests.append({
                    'updateParagraphStyle': {
                        'objectId': object_id,
                        'textRange': {'type': 'ALL'},
                        'style': {
                            'alignment': p_align
                        },
                        'fields': 'alignment'
                    }
                })
                
                # Mask BG fill if required
                if mask_bg:
                    requests.append({
                        'updateShapeProperties': {
                            'objectId': object_id,
                            'shapeProperties': {
                                'shapeBackgroundFill': {
                                    'solidFill': {
                                        'color': hex_to_slides_color(COLORS['white'])
                                    }
                                }
                            },
                            'fields': 'shapeBackgroundFill'
                        }
                    })
                    
            elif el_type == "group":
                requests.append({
                    'groupObjects': {
                        'groupObjectId': object_id,
                        'childrenObjectIds': el.get("childrenObjectIds", [])
                    }
                })
                
            elif el_type == "image":
                local_path = el.get("local_path")
                if local_path and os.path.exists(local_path):
                    try:
                        print(f"[Slides Uploader] Uploading temporary LaTeX image to Google Drive: {local_path}")
                        media = MediaFileUpload(local_path, mimetype='image/png')
                        drive_file = self.drive_service.files().create(
                            body={
                                'name': os.path.basename(local_path),
                                'parents': [folder_id] if folder_id else []
                            },
                            media_body=media,
                            fields='id, webContentLink'
                        ).execute()
                        
                        file_id = drive_file.get('id')
                        drive_files_to_cleanup.append(file_id)
                        
                        # Set public viewing permission so Slides can pull the image
                        self.drive_service.permissions().create(
                            fileId=file_id,
                            body={'role': 'reader', 'type': 'anyone'}
                        ).execute()
                        
                        # Re-fetch file to get webContentLink if not fully set
                        file_metadata = self.drive_service.files().get(
                            fileId=file_id,
                            fields='webContentLink'
                        ).execute()
                        url = file_metadata.get('webContentLink')
                        
                        if url:
                            requests.append({
                                'createImage': {
                                    'objectId': object_id,
                                    'url': url,
                                    'elementProperties': {
                                        'pageObjectId': page_id,
                                        'size': {
                                            'width': {'magnitude': el.get("width", 100), 'unit': 'PT'},
                                            'height': {'magnitude': el.get("height", 100), 'unit': 'PT'}
                                        },
                                        'transform': {
                                            'scaleX': 1, 'scaleY': 1,
                                            'translateX': el.get("x", 0), 'translateY': el.get("y", 0),
                                            'unit': 'PT'
                                        }
                                    }
                                }
                            })
                    except Exception as img_err:
                        print(f"[Slides Uploader] Error uploading image element '{object_id}': {img_err}")
                    
        # 3. Batch apply all requests to Google Slides presentation
        if requests:
            print(f"[Slides Uploader] Batch applying {len(requests)} drawing requests to Google Slides...")
            self.slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            
        # 4. If folder_id is specified, move the presentation to the desired folder
        if folder_id:
            try:
                print(f"[Slides Uploader] Moving presentation to Google Drive folder ID: {folder_id}")
                file_obj = self.drive_service.files().get(
                    fileId=presentation_id, fields='parents'
                ).execute()
                
                previous_parents = ",".join(file_obj.get('parents', []))
                self.drive_service.files().update(
                    fileId=presentation_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields='id, parents'
                ).execute()
            except Exception as e:
                print(f"[Slides Uploader] Could not move presentation to folder: {e}")
                
        # 5. Fetch complete presentation details to return links
        final_file = self.drive_service.files().get(
            fileId=presentation_id,
            fields='id, name, webViewLink'
        ).execute()
        
        # 6. Clean up temporary uploaded Drive images
        if drive_files_to_cleanup:
            print(f"[Slides Uploader] Cleaning up {len(drive_files_to_cleanup)} temporary LaTeX images from Google Drive...")
            for fid in drive_files_to_cleanup:
                try:
                    self.drive_service.files().delete(fileId=fid).execute()
                except Exception as clean_err:
                    print(f"[Slides Uploader] Could not delete file {fid} from Drive: {clean_err}")
        
        print(f"[Slides Uploader] Native Google Slides generated successfully!")
        print(f"File Name: {final_file.get('name')}")
        print(f"File ID: {final_file.get('id')}")
        print(f"Google Slides Link: {final_file.get('webViewLink')}")
        return final_file

    def append_slide_from_canvas_data(self, presentation_id, canvas_data):
        """
        Appends a new blank slide to an existing presentation and populates it.
        """
        import uuid
        slide_id = f"slide_{uuid.uuid4().hex[:12]}"  # Slide ID can be up to 50 alphanumeric characters
        create_req = [{'createSlide': {'objectId': slide_id}}]
        self.slides_service.presentations().batchUpdate(
            presentationId=presentation_id, body={'requests': create_req}
        ).execute()
        
        font_family = canvas_data.get("font_family", "Ubuntu")
        elements = canvas_data.get("elements", [])
        
        print(f"[Slides Uploader] Appending slide '{slide_id}' to presentation {presentation_id} with {len(elements)} elements...")
        
        requests = []
        drive_files_to_cleanup = []
        folder_id = None
        
        # Retrieve parent folder of the presentation so appended images/latex are saved there
        try:
            presentation_file = self.drive_service.files().get(
                fileId=presentation_id,
                fields='parents'
            ).execute()
            parents = presentation_file.get('parents', [])
            if parents:
                folder_id = parents[0]
                print(f"[Slides Uploader] Found presentation's parent folder ID for appending: {folder_id}")
        except Exception as e:
            print(f"[Slides Uploader] Warning: Could not retrieve parents for presentation {presentation_id}: {e}")
        
        for idx, el in enumerate(elements):
            el_type = el.get("type")
            object_id = el.get("id") or el.get("objectId") or f"element_{idx}_{el_type}"
            # Ensure unique object IDs
            object_id = f"{slide_id}_{object_id}"
            
            if el_type == "rect":
                requests.append({
                    'createShape': {
                        'objectId': object_id,
                        'shapeType': 'RECTANGLE',
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                'width': {'magnitude': el.get("width", 100), 'unit': 'PT'},
                                'height': {'magnitude': el.get("height", 100), 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1, 'scaleY': 1,
                                'translateX': el.get("x", 0), 'translateY': el.get("y", 0),
                                'unit': 'PT'
                            }
                        }
                    }
                })
                
                fill = el.get("fill", "none")
                stroke = el.get("stroke", COLORS['black'])
                stroke_width = el.get("stroke_width", 2.0)
                dasharray = el.get("dasharray", "none")
                
                shape_props = {}
                if fill != "none":
                    shape_props['shapeBackgroundFill'] = {
                        'solidFill': {
                            'color': hex_to_slides_color(fill)
                        }
                    }
                else:
                    shape_props['shapeBackgroundFill'] = {
                        'propertyState': 'NOT_RENDERED'
                    }
                    
                if stroke != "none":
                    shape_props['outline'] = {
                        'outlineFill': {
                            'solidFill': {
                                'color': hex_to_slides_color(stroke)
                            }
                        },
                        'weight': {
                            'magnitude': stroke_width,
                            'unit': 'PT'
                        },
                        'dashStyle': svg_dasharray_to_slides(dasharray)
                    }
                else:
                    shape_props['outline'] = {
                        'propertyState': 'NOT_RENDERED'
                    }
                
                requests.append({
                    'updateShapeProperties': {
                        'objectId': object_id,
                        'shapeProperties': shape_props,
                        'fields': 'shapeBackgroundFill,outline'
                    }
                })
                
            elif el_type in ["ellipse", "circle"]:
                requests.append({
                    'createShape': {
                        'objectId': object_id,
                        'shapeType': 'ELLIPSE',
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                'width': {'magnitude': el.get("width", 100), 'unit': 'PT'},
                                'height': {'magnitude': el.get("height", 100), 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1, 'scaleY': 1,
                                'translateX': el.get("x", 0), 'translateY': el.get("y", 0),
                                'unit': 'PT'
                            }
                        }
                    }
                })
                
                fill = el.get("fill", "none")
                stroke = el.get("stroke", COLORS['black'])
                stroke_width = el.get("stroke_width", 2.0)
                dasharray = el.get("dasharray", "none")
                
                shape_props = {}
                if fill != "none":
                    shape_props['shapeBackgroundFill'] = {
                        'solidFill': {
                            'color': hex_to_slides_color(fill)
                        }
                    }
                else:
                    shape_props['shapeBackgroundFill'] = {
                        'propertyState': 'NOT_RENDERED'
                    }
                    
                if stroke != "none":
                    shape_props['outline'] = {
                        'outlineFill': {
                            'solidFill': {
                                'color': hex_to_slides_color(stroke)
                            }
                        },
                        'weight': {
                            'magnitude': stroke_width,
                            'unit': 'PT'
                        },
                        'dashStyle': svg_dasharray_to_slides(dasharray)
                    }
                else:
                    shape_props['outline'] = {
                        'propertyState': 'NOT_RENDERED'
                    }
                
                requests.append({
                    'updateShapeProperties': {
                        'objectId': object_id,
                        'shapeProperties': shape_props,
                        'fields': 'shapeBackgroundFill,outline'
                    }
                })
                
            elif el_type == "line":
                x1, y1 = el.get("x1", 0), el.get("y1", 0)
                x2, y2 = el.get("x2", 0), el.get("y2", 0)
                dx, dy = x2 - x1, y2 - y1
                w, h = abs(dx), abs(dy)
                if w == 0: w = 0.1
                if h == 0: h = 0.1
                
                scale_x = 1.0 if dx >= 0 else -1.0
                scale_y = 1.0 if dy >= 0 else -1.0
                
                requests.append({
                    'createLine': {
                        'objectId': object_id,
                        'lineCategory': 'STRAIGHT',
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                'width': {'magnitude': w, 'unit': 'PT'},
                                'height': {'magnitude': h, 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': scale_x, 'scaleY': scale_y,
                                'translateX': x1, 'translateY': y1,
                                'unit': 'PT'
                            }
                        }
                    }
                })
                
                stroke = el.get("stroke", COLORS['black'])
                stroke_width = el.get("stroke_width", 2.0)
                dasharray = el.get("dasharray", "none")
                
                requests.append({
                    'updateLineProperties': {
                        'objectId': object_id,
                        'lineProperties': {
                            'lineFill': {
                                'solidFill': {
                                    'color': hex_to_slides_color(stroke)
                                }
                            },
                            'weight': {
                                'magnitude': stroke_width,
                                'unit': 'PT'
                            },
                            'dashStyle': svg_dasharray_to_slides(dasharray)
                        },
                        'fields': 'lineFill,weight,dashStyle'
                    }
                })
                
            elif el_type == "arrow":
                x1, y1 = el.get("x1", 0), el.get("y1", 0)
                x2, y2 = el.get("x2", 0), el.get("y2", 0)
                dx, dy = x2 - x1, y2 - y1
                w, h = abs(dx), abs(dy)
                if w == 0: w = 0.1
                if h == 0: h = 0.1
                
                scale_x = 1.0 if dx >= 0 else -1.0
                scale_y = 1.0 if dy >= 0 else -1.0
                
                requests.append({
                    'createLine': {
                        'objectId': object_id,
                        'lineCategory': 'STRAIGHT',
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                'width': {'magnitude': w, 'unit': 'PT'},
                                'height': {'magnitude': h, 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': scale_x, 'scaleY': scale_y,
                                'translateX': x1, 'translateY': y1,
                                'unit': 'PT'
                            }
                        }
                    }
                })
                
                stroke = el.get("stroke", COLORS['black'])
                stroke_width = el.get("stroke_width", 3.0)
                
                requests.append({
                    'updateLineProperties': {
                        'objectId': object_id,
                        'lineProperties': {
                            'lineFill': {
                                'solidFill': {
                                    'color': hex_to_slides_color(stroke)
                                }
                            },
                            'weight': {
                                'magnitude': stroke_width,
                                'unit': 'PT'
                            },
                            'endArrow': 'STEALTH_ARROW'
                        },
                        'fields': 'lineFill,weight,endArrow'
                    }
                })
                
            elif el_type == "text":
                x = el.get("x", 0)
                y = el.get("y", 0)
                text = el.get("text", "")
                font_sz = el.get("font_size", 16)
                color = el.get("color", COLORS['black'])
                bold = el.get("bold", False)
                italic = el.get("italic", False)
                align = el.get("align", "start")
                mask_bg = el.get("mask_bg", False)
                is_latex = el.get("is_latex", False) or el.get("isLatex", False) or (text.startswith("\\") and len(text) > 1)
                
                if is_latex:
                    try:
                        from graph_engine import compile_latex_to_png
                        latex_meta = compile_latex_to_png(text, font_sz, color, align, group_id=object_id)
                        if latex_meta:
                            local_path = latex_meta['local_path']
                            w_slide = latex_meta['width']
                            h_slide = latex_meta['height']
                            tx = x + latex_meta['x_offset']
                            ty = y + latex_meta['y_offset']
                            
                            print(f"[Slides Uploader] Uploading temporary LaTeX text image to Google Drive (Append): {local_path}")
                            media = MediaFileUpload(local_path, mimetype='image/png')
                            drive_file = self.drive_service.files().create(
                                body={
                                    'name': os.path.basename(local_path),
                                    'parents': [folder_id] if folder_id else []
                                },
                                media_body=media,
                                fields='id, webContentLink'
                            ).execute()
                            
                            file_id = drive_file.get('id')
                            drive_files_to_cleanup.append(file_id)
                            
                            self.drive_service.permissions().create(
                                fileId=file_id,
                                body={'role': 'reader', 'type': 'anyone'}
                            ).execute()
                            
                            file_metadata = self.drive_service.files().get(
                                fileId=file_id,
                                fields='webContentLink'
                            ).execute()
                            url = file_metadata.get('webContentLink')
                            
                            if url:
                                if mask_bg:
                                    bg_id = f"{object_id}_bg"
                                    requests.append({
                                        'createShape': {
                                            'objectId': bg_id,
                                            'shapeType': 'RECTANGLE',
                                            'elementProperties': {
                                                'pageObjectId': slide_id,
                                                'size': {
                                                    'width': {'magnitude': w_slide, 'unit': 'PT'},
                                                    'height': {'magnitude': h_slide, 'unit': 'PT'}
                                                },
                                                'transform': {
                                                    'scaleX': 1, 'scaleY': 1,
                                                    'translateX': tx, 'translateY': ty,
                                                    'unit': 'PT'
                                                }
                                            }
                                        }
                                    })
                                    requests.append({
                                        'updateShapeProperties': {
                                            'objectId': bg_id,
                                            'shapeProperties': {
                                                'shapeBackgroundFill': {
                                                    'solidFill': {
                                                        'color': hex_to_slides_color(COLORS['white'])
                                                    }
                                                },
                                                'outline': {
                                                    'propertyState': 'NOT_RENDERED'
                                                }
                                            },
                                            'fields': 'shapeBackgroundFill,outline'
                                        }
                                    })
                                requests.append({
                                    'createImage': {
                                        'objectId': object_id,
                                        'url': url,
                                        'elementProperties': {
                                            'pageObjectId': slide_id,
                                            'size': {
                                                'width': {'magnitude': w_slide, 'unit': 'PT'},
                                                'height': {'magnitude': h_slide, 'unit': 'PT'}
                                            },
                                            'transform': {
                                                'scaleX': 1, 'scaleY': 1,
                                                'translateX': tx, 'translateY': ty,
                                                'unit': 'PT'
                                            }
                                        }
                                    }
                                })
                                continue  # Process next element
                    except Exception as latex_err:
                        print(f"[Slides Uploader] Error rendering/uploading LaTeX text element in Append '{object_id}': {latex_err}")
                        # Fallback to normal text box rendering below

                box_w = el.get("width", 400)
                box_h = el.get("height", font_sz * 2.5 if font_sz * 2.5 > 40 else 40)
                
                if align == "center":
                    tx = x - (box_w / 2.0)
                elif align == "right":
                    tx = x - box_w
                else:
                    tx = x
                    
                ty = y - (box_h / 2.0)
                
                requests.append({
                    'createShape': {
                        'objectId': object_id,
                        'shapeType': 'TEXT_BOX',
                        'elementProperties': {
                            'pageObjectId': slide_id,
                            'size': {
                                'width': {'magnitude': box_w, 'unit': 'PT'},
                                'height': {'magnitude': box_h, 'unit': 'PT'}
                            },
                            'transform': {
                                'scaleX': 1, 'scaleY': 1,
                                'translateX': tx, 'translateY': ty,
                                'unit': 'PT'
                            }
                        }
                    }
                })
                
                requests.append({
                    'insertText': {
                        'objectId': object_id,
                        'insertionIndex': 0,
                        'text': text
                    }
                })
                
                requests.append({
                    'updateTextStyle': {
                        'objectId': object_id,
                        'textRange': {'type': 'ALL'},
                        'style': {
                            'bold': bold,
                            'italic': italic,
                            'fontSize': {'magnitude': font_sz, 'unit': 'PT'},
                            'foregroundColor': {
                                'opaqueColor': hex_to_slides_color(color)
                            },
                            'fontFamily': font_family
                        },
                        'fields': 'bold,italic,fontSize,foregroundColor,fontFamily'
                    }
                })
                
                p_align = 'CENTER' if align == 'center' else ('END' if align == 'right' else 'START')
                requests.append({
                    'updateParagraphStyle': {
                        'objectId': object_id,
                        'textRange': {'type': 'ALL'},
                        'style': {
                            'alignment': p_align
                        },
                        'fields': 'alignment'
                    }
                })
                
                if mask_bg:
                    requests.append({
                        'updateShapeProperties': {
                            'objectId': object_id,
                            'shapeProperties': {
                                'shapeBackgroundFill': {
                                    'solidFill': {
                                        'color': hex_to_slides_color(COLORS['white'])
                                    }
                                }
                            },
                            'fields': 'shapeBackgroundFill'
                        }
                    })
                    
            elif el_type == "group":
                children_ids = [f"{slide_id}_{cid}" for cid in el.get("childrenObjectIds", [])]
                requests.append({
                    'groupObjects': {
                        'groupObjectId': object_id,
                        'childrenObjectIds': children_ids
                    }
                })
                
            elif el_type == "image":
                local_path = el.get("local_path")
                if local_path and os.path.exists(local_path):
                    try:
                        media = MediaFileUpload(local_path, mimetype='image/png')
                        drive_file = self.drive_service.files().create(
                            body={
                                'name': os.path.basename(local_path),
                                'parents': [folder_id] if folder_id else []
                            },
                            media_body=media,
                            fields='id, webContentLink'
                        ).execute()
                        
                        file_id = drive_file.get('id')
                        drive_files_to_cleanup.append(file_id)
                        
                        self.drive_service.permissions().create(
                            fileId=file_id,
                            body={'role': 'reader', 'type': 'anyone'}
                        ).execute()
                        
                        file_metadata = self.drive_service.files().get(
                            fileId=file_id,
                            fields='webContentLink'
                        ).execute()
                        url = file_metadata.get('webContentLink')
                        
                        if url:
                            requests.append({
                                'createImage': {
                                    'objectId': object_id,
                                    'url': url,
                                    'elementProperties': {
                                        'pageObjectId': slide_id,
                                        'size': {
                                            'width': {'magnitude': el.get("width", 100), 'unit': 'PT'},
                                            'height': {'magnitude': el.get("height", 100), 'unit': 'PT'}
                                        },
                                        'transform': {
                                            'scaleX': 1, 'scaleY': 1,
                                            'translateX': el.get("x", 0), 'translateY': el.get("y", 0),
                                            'unit': 'PT'
                                        }
                                    }
                                }
                            })
                    except Exception as img_err:
                        print(f"[Slides Uploader] Error uploading image element '{object_id}': {img_err}")
                        
        if requests:
            print(f"[Slides Uploader] Batch applying {len(requests)} drawing requests to Google Slides slide {slide_id}...")
            self.slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            
        if drive_files_to_cleanup:
            print(f"[Slides Uploader] Cleaning up {len(drive_files_to_cleanup)} temporary LaTeX images from Google Drive...")
            for fid in drive_files_to_cleanup:
                try:
                    self.drive_service.files().delete(fileId=fid).execute()
                except Exception as clean_err:
                    print(f"[Slides Uploader] Could not delete file {fid} from Drive: {clean_err}")
                    
        # Return presentation metadata
        final_file = self.drive_service.files().get(
            fileId=presentation_id,
            fields='id, name, webViewLink'
        ).execute()
        return final_file

if __name__ == "__main__":
    if not API_AVAILABLE:
        print("Google API Client libraries are not installed.")
        sys.exit(1)
        
    if len(sys.argv) < 2:
        print("Usage: python gslides_uploader.py <path_to_json_file> [target_name] [google_drive_folder_id]")
        sys.exit(1)
        
    json_path = sys.argv[1]
    target_name = sys.argv[2] if len(sys.argv) > 2 else "AI Generated Slide"
    folder_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        sys.exit(1)
        
    with open(json_path, 'r', encoding='utf-8') as f:
        canvas_data = json.load(f)
        
    try:
        creds_file = "credentials.json"
        if not os.path.exists(creds_file):
            creds_file = "service_account.json" if os.path.exists("service_account.json") else None
            
        uploader = GoogleSlidesUploader(credentials_path=creds_file)
        uploader.create_presentation_from_canvas_data(canvas_data, name=target_name, folder_id=folder_id)
    except Exception as e:
        print(f"\nSlides uploader failed: {e}")
        traceback.print_exc()
