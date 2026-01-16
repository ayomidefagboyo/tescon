"""Google Drive integration service for uploading processed images."""
import os
import io
from typing import List, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import service_account
import logging

# Scopes required for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.file']

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Service for uploading files to Google Drive."""

    def __init__(self):
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Drive service with authentication."""
        try:
            # Try service account first (for production)
            service_account_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
            if service_account_path and os.path.exists(service_account_path):
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path, scopes=SCOPES
                )
                self.service = build('drive', 'v3', credentials=credentials)
                logger.info("Google Drive initialized with service account")
                return

            # Fallback to OAuth (for development)
            creds = None
            token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
            credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')

            # Load existing token
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)

            # If no valid credentials, run OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif os.path.exists(credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    # Save credentials for next run
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                else:
                    logger.warning("No Google Drive credentials found. Set GOOGLE_SERVICE_ACCOUNT_PATH or add credentials.json")
                    return

            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive initialized with OAuth")

        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            self.service = None

    def is_available(self) -> bool:
        """Check if Google Drive service is available."""
        return self.service is not None

    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder to create
            parent_folder_id: ID of parent folder (None for root)

        Returns:
            Folder ID if successful, None otherwise
        """
        if not self.service:
            return None

        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]

            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            logger.info(f"Created folder '{folder_name}' with ID: {folder.get('id')}")
            return folder.get('id')

        except Exception as e:
            logger.error(f"Failed to create folder '{folder_name}': {e}")
            return None

    def find_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """Find a folder by name.

        Args:
            folder_name: Name of the folder to find
            parent_folder_id: ID of parent folder (None for root)

        Returns:
            Folder ID if found, None otherwise
        """
        if not self.service:
            return None

        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_folder_id:
                query += f" and '{parent_folder_id}' in parents"

            results = self.service.files().list(q=query, fields='files(id, name)').execute()
            files = results.get('files', [])

            if files:
                return files[0]['id']
            return None

        except Exception as e:
            logger.error(f"Failed to find folder '{folder_name}': {e}")
            return None

    def get_or_create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """Get existing folder or create new one.

        Args:
            folder_name: Name of the folder
            parent_folder_id: ID of parent folder (None for root)

        Returns:
            Folder ID if successful, None otherwise
        """
        # Try to find existing folder first
        folder_id = self.find_folder(folder_name, parent_folder_id)
        if folder_id:
            return folder_id

        # Create new folder if not found
        return self.create_folder(folder_name, parent_folder_id)

    def upload_file(self, file_path: str, filename: str, folder_id: Optional[str] = None) -> Optional[str]:
        """Upload a file to Google Drive.

        Args:
            file_path: Local path to the file
            filename: Name for the file in Drive
            folder_id: ID of the folder to upload to (None for root)

        Returns:
            File ID if successful, None otherwise
        """
        if not self.service:
            return None

        try:
            # Determine MIME type based on file extension
            mime_type = 'image/png'
            if filename.lower().endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'

            file_metadata = {'name': filename}
            if folder_id:
                file_metadata['parents'] = [folder_id]

            with open(file_path, 'rb') as file_data:
                media = MediaIoBaseUpload(
                    io.BytesIO(file_data.read()),
                    mimetype=mime_type,
                    resumable=True
                )

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()

            file_id = file.get('id')
            web_link = file.get('webViewLink')
            logger.info(f"Uploaded '{filename}' to Drive with ID: {file_id}")
            return file_id

        except Exception as e:
            logger.error(f"Failed to upload file '{filename}': {e}")
            return None

    def upload_part_images(self, part_number: str, image_files: List[str]) -> bool:
        """Upload processed images for a part to Google Drive.

        Args:
            part_number: Part number (used as folder name)
            image_files: List of local file paths to upload

        Returns:
            True if all uploads successful, False otherwise
        """
        if not self.service:
            logger.warning("Google Drive service not available")
            return False

        try:
            # Get or create main parts folder
            main_folder_id = os.getenv('GOOGLE_DRIVE_PARTS_FOLDER_ID')
            if not main_folder_id:
                # Create main parts folder if not specified
                main_folder_id = self.get_or_create_folder("TESCON_Parts")
                if not main_folder_id:
                    logger.error("Failed to create main parts folder")
                    return False

            # Get or create folder for this specific part
            part_folder_id = self.get_or_create_folder(part_number, main_folder_id)
            if not part_folder_id:
                logger.error(f"Failed to create folder for part {part_number}")
                return False

            # Upload all images to the part folder
            success_count = 0
            for image_path in image_files:
                if os.path.exists(image_path):
                    filename = os.path.basename(image_path)
                    file_id = self.upload_file(image_path, filename, part_folder_id)
                    if file_id:
                        success_count += 1
                    else:
                        logger.error(f"Failed to upload {filename}")
                else:
                    logger.error(f"Image file not found: {image_path}")

            total_files = len(image_files)
            success = success_count == total_files

            if success:
                logger.info(f"Successfully uploaded {success_count}/{total_files} images for part {part_number}")
            else:
                logger.warning(f"Partially uploaded {success_count}/{total_files} images for part {part_number}")

            return success

        except Exception as e:
            logger.error(f"Failed to upload images for part {part_number}: {e}")
            return False


# Global instance
drive_service = GoogleDriveService()


def get_drive_service() -> GoogleDriveService:
    """Get the global Google Drive service instance."""
    return drive_service