"""Google Drive OAuth service for personal Google account storage."""
import os
import json
import pickle
from typing import List, Dict, Optional, Tuple
from io import BytesIO
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError


class GoogleDriveOAuth:
    """Handle saving to Google Drive using OAuth (personal account)."""

    def __init__(
        self,
        folder_id: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize Google Drive OAuth storage.

        Args:
            folder_id: Google Drive folder ID where images will be saved
            credentials_path: Path to OAuth client secrets JSON file
        """
        self.folder_id = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_OAUTH_CREDENTIALS_PATH", "credentials.json")

        # OAuth scopes
        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']

        # Initialize Drive service
        self.drive_service = None

        if self.folder_id and self.credentials_path:
            self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Drive API service with OAuth."""
        try:
            creds = self._get_oauth_credentials()
            if not creds:
                print("⚠ Warning: OAuth credentials not available. Drive storage will be unavailable.")
                return

            self.drive_service = build('drive', 'v3', credentials=creds)
            print(f"✓ Google Drive OAuth API configured successfully (Folder: {self.folder_id})")

        except Exception as e:
            print(f"⚠ Warning: Failed to initialize Google Drive OAuth: {e}")
            print("Drive storage will be unavailable. Check OAuth setup.")

    def _get_oauth_credentials(self) -> Optional[Credentials]:
        """Get OAuth credentials, handling token refresh and initial auth."""
        creds = None
        token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.pickle')

        try:
            # Load existing token
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)

            # If no valid credentials, handle refresh or new auth
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        print("Refreshing OAuth token...")
                        creds.refresh(Request())
                    except Exception as e:
                        print(f"Token refresh failed: {e}")
                        creds = None

                if not creds:
                    # Need new OAuth flow
                    if not os.path.exists(self.credentials_path):
                        print(f"OAuth credentials file not found: {self.credentials_path}")
                        return None

                    print("Starting OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)

                # Save credentials for next run
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                print("OAuth credentials saved.")

            return creds

        except Exception as e:
            print(f"OAuth authentication failed: {e}")
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
                print(f"Found existing folder for part {part_number}: {folders[0]['id']}")
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

            folder_id = folder.get('id')
            print(f"Created new folder for part {part_number}: {folder_id}")
            return folder_id

        except Exception as e:
            print(f"Error creating/getting folder for part {part_number}: {e}")
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
            raise Exception("Google Drive OAuth service not initialized")

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
                    'parents': [part_folder_id],
                    'description': f'Part: {part_number} - {description}'
                }

                # Create media upload
                media = MediaIoBaseUpload(
                    BytesIO(file_bytes),
                    mimetype='image/png' if filename.endswith('.png') else 'image/jpeg',
                    resumable=True
                )

                # Upload file
                file_result = self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, webViewLink'
                ).execute()

                saved_files.append({
                    'filename': filename,
                    'id': file_result.get('id'),
                    'url': file_result.get('webViewLink', '')
                })

                print(f"✓ Uploaded {filename} to Google Drive")

            except Exception as e:
                print(f"✗ Failed to upload {filename}: {e}")
                raise Exception(f"Failed to upload {filename}: {e}")

        return saved_files

    def check_duplicates(self, part_number: str, view_numbers: List[int]) -> Dict[int, bool]:
        """
        Check if files already exist for given view numbers.

        Args:
            part_number: Part number
            view_numbers: List of view numbers to check

        Returns:
            Dict mapping view_number to exists boolean
        """
        if not self.drive_service or not self.folder_id:
            return {view: False for view in view_numbers}

        try:
            # Get part folder
            part_folder_id = self._get_or_create_part_folder(part_number)
            if not part_folder_id:
                return {view: False for view in view_numbers}

            # Get existing files in part folder
            query = f"parents in '{part_folder_id}' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(name)"
            ).execute()

            existing_files = [f['name'] for f in results.get('files', [])]

            # Check which view numbers exist
            duplicates = {}
            for view_num in view_numbers:
                # Look for files containing the view number pattern
                view_exists = any(f"_{view_num}_" in filename for filename in existing_files)
                duplicates[view_num] = view_exists

            return duplicates

        except Exception as e:
            print(f"Error checking duplicates: {e}")
            return {view: False for view in view_numbers}

    def list_part_images(self, part_number: str) -> List[Dict]:
        """
        List all images for a part.

        Args:
            part_number: Part number

        Returns:
            List of file info dicts
        """
        if not self.drive_service or not self.folder_id:
            return []

        try:
            # Get part folder
            part_folder_id = self._get_or_create_part_folder(part_number)
            if not part_folder_id:
                return []

            # Get files in part folder
            query = f"parents in '{part_folder_id}' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, webViewLink, createdTime)"
            ).execute()

            return results.get('files', [])

        except Exception as e:
            print(f"Error listing part images: {e}")
            return []


def get_oauth_drive_storage() -> Optional[GoogleDriveOAuth]:
    """Get OAuth Google Drive storage instance."""
    try:
        storage = GoogleDriveOAuth()
        if storage.drive_service:
            return storage
        return None
    except Exception as e:
        print(f"Failed to initialize OAuth Google Drive storage: {e}")
        return None