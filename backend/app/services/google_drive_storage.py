"""Google Drive storage service for saving processed images."""
import os
import json
import base64
from typing import List, Dict, Optional, Tuple
from io import BytesIO
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError


class GoogleDriveStorage:
    """Handle saving to Google Drive."""
    
    def __init__(
        self,
        folder_id: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize Google Drive storage.
        
        Args:
            folder_id: Google Drive folder ID where images will be saved
            credentials_path: Path to service account JSON file
        """
        self.folder_id = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH")
        
        # Initialize Drive service
        self.drive_service = None
        
        if self.folder_id and self.credentials_path:
            self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive API service."""
        try:
            creds = self._load_credentials()
            if not creds:
                print("⚠ Warning: Google Drive credentials not found. Drive storage will be unavailable.")
                return
            
            self.drive_service = build('drive', 'v3', credentials=creds)
            print(f"✓ Google Drive API configured successfully (Folder: {self.folder_id})")
            
        except Exception as e:
            print(f"⚠ Warning: Failed to initialize Google Drive: {e}")
            print("Drive storage will be unavailable. Check GOOGLE_CLOUD_SETUP.md for setup instructions.")
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from file or environment variable."""
        try:
            # Try loading from file path
            if self.credentials_path and os.path.exists(self.credentials_path):
                return Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
            
            # Try loading from base64 encoded environment variable (for Render)
            creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
            if creds_json:
                try:
                    # Decode base64
                    creds_data = base64.b64decode(creds_json)
                    creds_dict = json.loads(creds_data)
                    return Credentials.from_service_account_info(
                        creds_dict,
                        scopes=['https://www.googleapis.com/auth/drive']
                    )
                except Exception as e:
                    print(f"Error decoding credentials from env: {e}")
            
            return None
            
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def _get_or_create_part_folder(self, part_number: str) -> Optional[str]:
        """
        Get or create folder for a part number.
        
        Args:
            part_number: Part number
            
        Returns:
            Folder ID or None if error
        """
        if not self.drive_service or not self.folder_id:
            return None
        
        try:
            # Check if folder already exists
            query = f"name='{part_number}' and parents in '{self.folder_id}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']
            
            # Create new folder
            folder_metadata = {
                'name': part_number,
                'parents': [self.folder_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            return folder.get('id')
            
        except HttpError as e:
            print(f"Error creating/getting part folder: {e}")
            return None
    
    def save_part_images(
        self,
        part_number: str,
        image_files: List[Tuple[str, bytes]],
        description: str = ""
    ) -> List[Dict]:
        """
        Save images for a part to Google Drive.
        
        Args:
            part_number: Part number
            image_files: List of (filename, bytes) tuples
            description: Part description (for metadata)
            
        Returns:
            List of dicts with file info: [{"filename": "...", "id": "...", "url": "..."}, ...]
        """
        if not self.drive_service:
            raise Exception("Google Drive service not initialized")
        
        # Get or create part folder
        part_folder_id = self._get_or_create_part_folder(part_number)
        if not part_folder_id:
            raise Exception(f"Failed to create/get folder for part {part_number}")
        
        saved_files = []
        
        for filename, file_bytes in image_files:
            try:
                # Create file metadata
                file_metadata = {
                    'name': filename,
                    'parents': [part_folder_id]
                }
                
                # Create media upload
                media = MediaIoBaseUpload(
                    BytesIO(file_bytes),
                    mimetype='image/jpeg' if filename.lower().endswith(('.jpg', '.jpeg')) else 'image/png',
                    resumable=True
                )
                
                # Upload file
                file = self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, webViewLink'
                ).execute()
                
                saved_files.append({
                    "filename": filename,
                    "id": file.get('id'),
                    "url": file.get('webViewLink'),
                    "part_number": part_number
                })
                
            except HttpError as e:
                print(f"Error uploading {filename}: {e}")
                raise Exception(f"Failed to upload {filename}: {str(e)}")
        
        return saved_files
    
    def check_duplicates(self, part_number: str, view_numbers: List[int]) -> Dict[int, bool]:
        """
        Check if images already exist for a part.
        
        Args:
            part_number: Part number
            view_numbers: List of view numbers to check (e.g., [1, 2, 3])
            
        Returns:
            Dictionary mapping view_number -> exists (bool)
        """
        if not self.drive_service:
            return {v: False for v in view_numbers}
        
        # Get part folder
        part_folder_id = self._get_or_create_part_folder(part_number)
        if not part_folder_id:
            return {v: False for v in view_numbers}
        
        try:
            # List all files in part folder
            query = f"parents in '{part_folder_id}' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(name)"
            ).execute()
            
            existing_files = {f['name'] for f in results.get('files', [])}
            
            # Check for each view number
            duplicates = {}
            for view_num in view_numbers:
                # Check if any file matches the pattern: PartNumber_ViewNumber_*
                pattern = f"{part_number}_{view_num}_"
                exists = any(pattern in f for f in existing_files)
                duplicates[view_num] = exists
            
            return duplicates
            
        except HttpError as e:
            print(f"Error checking duplicates: {e}")
            return {v: False for v in view_numbers}
    
    def list_part_images(self, part_number: str) -> List[Dict]:
        """
        List all images for a part.
        
        Args:
            part_number: Part number
            
        Returns:
            List of file info dicts
        """
        if not self.drive_service:
            return []
        
        part_folder_id = self._get_or_create_part_folder(part_number)
        if not part_folder_id:
            return []
        
        try:
            query = f"parents in '{part_folder_id}' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, webViewLink, createdTime)"
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as e:
            print(f"Error listing part images: {e}")
            return []


# Global instance
_drive_storage: Optional[GoogleDriveStorage] = None


def get_drive_storage() -> Optional[GoogleDriveStorage]:
    """Get or create global Google Drive storage instance."""
    global _drive_storage
    if _drive_storage is None:
        _drive_storage = GoogleDriveStorage()
    return _drive_storage
