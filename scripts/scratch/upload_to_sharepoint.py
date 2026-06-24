import os
import argparse
import msal
import requests
import json
import six
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

# Import our existing image compressor
# We need to add the parent directory to sys.path to import app modules if running as script
import sys
current_dir = Path(__file__).resolve().parent
if str(current_dir.parent) not in sys.path:
    sys.path.append(str(current_dir.parent))

try:
    from app.utils.image_compressor import compress_image
except ImportError:
    # Fallback if import fails (e.g. slight path mismatch)
    print("⚠️  Warning: Could not import image_compressor. Using local fallback.")
    def compress_image(image, quality=85, max_dimension=None, optimize=True):
        if max_dimension and (image.width > max_dimension or image.height > max_dimension):
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        return image

# Load environment variables
load_dotenv()

# Configuration
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SITE_ID = os.getenv("SHAREPOINT_SITE_ID")
DRIVE_ID = os.getenv("SHAREPOINT_DRIVE_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_access_token():
    """Authenticate and get access token using MSAL."""
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        print("❌ Missing Azure credentials in .env file.")
        return None

    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )

    result = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" in result:
        return result["access_token"]
    else:
        print(f"❌ Authentication failed: {result.get('error_description')}")
        return None

def process_and_compress(file_path: Path, quality: int = 85, max_dimension: int = 2048) -> bytes:
    """Read and compress image file."""
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if needed (JPEG doesn't support RGBA)
            if img.mode in ('RGBA', 'P') and not file_path.name.lower().endswith('.png'):
                img = img.convert('RGB')
            
            # Compress using our utility
            compressed_img = compress_image(
                img,
                quality=quality,
                max_dimension=max_dimension,
                optimize=True
            )
            
            # Save to buffer
            buffer = BytesIO()
            # Determine format
            fmt = "PNG" if file_path.name.lower().endswith('.png') else "JPEG"
            
            if fmt == "JPEG":
                compressed_img.save(buffer, format=fmt, quality=quality, optimize=True)
            else:
                # PNG optimization
                compressed_img.save(buffer, format=fmt, optimize=True)
                
            buffer.seek(0)
            return buffer.read()
    except Exception as e:
        print(f"⚠️  Compression failed for {file_path.name}: {e}. Using original.")
        # Fallback to reading original file
        with open(file_path, 'rb') as f:
            return f.read()

def upload_file(file_path: Path, token: str, drive_id: str, remote_folder_path: str, 
                compress: bool = False, quality: int = 85):
    """
    Upload a file to SharePoint.
    
    Args:
        file_path: Local path to the file.
        token: Access token.
        drive_id: SharePoint Drive (Document Library) ID.
        remote_folder_path: Path in SharePoint relative to the drive root.
        compress: Whether to compress the image before uploading.
        quality: Compression quality (1-100).
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream"
    }
    
    filename = file_path.name
    # Ensure remote path doesn't start with /
    remote_path = f"{remote_folder_path}/{filename}".lstrip("/")
    
    # Graph API endpoint for small file upload (<4MB)
    upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{remote_path}:/content"

    try:
        if compress and filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            # Compress logic
            file_content = process_and_compress(file_path, quality)
            # Log size saving
            original_size = os.path.getsize(file_path)
            new_size = len(file_content)
            reduction = (1 - new_size / original_size) * 100
            if reduction > 0:
                print(f"📉 Compressed {filename}: {original_size/1024:.1f}KB -> {new_size/1024:.1f}KB (-{reduction:.1f}%)")
        else:
            with open(file_path, 'rb') as f:
                file_content = f.read()
        
        response = requests.put(upload_url, headers=headers, data=file_content)
        
        if response.status_code in [200, 201]:
            print(f"✅ Uploaded: {filename}")
            return True
        else:
            print(f"❌ Failed to upload {filename}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error uploading {filename}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Upload images to SharePoint.")
    parser.add_argument("--source", type=str, default="downloads", help="Local source directory")
    parser.add_argument("--dry-run", action="store_true", help="Test mode, doesn't upload")
    parser.add_argument("--compress", action="store_true", help="Enable image compression")
    parser.add_argument("--quality", type=int, default=85, help="Compression quality (1-100), default 85")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 Dry Run Mode: Checking configuration and files...")
        
    token = get_access_token()
    if not token:
        return

    if args.dry_run:
        print("✅ Authentication successful.")
    
    if not DRIVE_ID:
        print("❌ Missing SHAREPOINT_DRIVE_ID in .env")
        return

    source_dir = Path(args.source)
    if not source_dir.exists():
        print(f"❌ Source directory '{source_dir}' does not exist.")
        return

    # Walk through the downloads directory
    print(f"📂 Scanning '{source_dir}'...")
    if args.compress:
        print(f"⚡ Compression enabled (Quality: {args.quality})")
    
    for r, d, f in os.walk(source_dir):
        for file in f:
             if file.endswith(('.jpg', '.jpeg', '.png')):
                local_path = Path(r) / file
                
                # Calculate remote path relative to source directory
                # Example: downloads/26030481/img.png -> Parts/26030481/img.png
                rel_path = local_path.relative_to(source_dir)
                remote_folder = f"Parts/{rel_path.parent}"
                
                if args.dry_run:
                    print(f"Would upload: {local_path} -> {remote_folder}/{file}")
                    if args.compress:
                        # Estimate compression in dry run
                        try:
                            compressed_bytes = process_and_compress(local_path, args.quality)
                            orig_size = os.path.getsize(local_path)
                            new_size = len(compressed_bytes)
                            print(f"   (Estimated size: {orig_size/1024:.1f}KB -> {new_size/1024:.1f}KB)")
                        except Exception as e:
                            print(f"   (Compression check failed: {e})")
                else:
                    upload_file(local_path, token, DRIVE_ID, remote_folder, 
                                compress=args.compress, quality=args.quality)

    print("\n✅ Operation completed.")

if __name__ == "__main__":
    main()
