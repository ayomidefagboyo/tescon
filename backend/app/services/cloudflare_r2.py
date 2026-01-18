"""Cloudflare R2 storage service for processed images."""
import os
import io
from typing import List, Dict, Any, Optional
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError


class CloudflareR2Storage:
    """Cloudflare R2 storage service using S3-compatible API."""

    def __init__(self):
        """Initialize R2 client."""
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.access_key = os.getenv("CLOUDFLARE_ACCESS_KEY_ID")
        self.secret_key = os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("CLOUDFLARE_BUCKET_NAME", "tescon-images")
        self.region = "auto"  # R2 uses "auto" region

        # Validate configuration
        if not all([self.account_id, self.access_key, self.secret_key]):
            raise ValueError("Missing Cloudflare R2 credentials. Check environment variables.")

        # Initialize S3 client for R2
        self.s3_client = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(
                retries={'max_attempts': 3},
                signature_version='s3v4'
            )
        )

        # Test connection
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                print(f"⚠ Warning: Bucket '{self.bucket_name}' not found. Create it in Cloudflare dashboard.")
            else:
                print(f"⚠ Warning: R2 connection error: {e}")
        except Exception as e:
            print(f"⚠ Warning: R2 initialization error: {e}")

    def save_part_images(
        self,
        part_number: str,
        image_files: List[tuple],
        description: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Save processed images to Cloudflare R2.

        Args:
            part_number: Part number for organizing files
            image_files: List of (filename, image_bytes) tuples
            description: Part description for metadata

        Returns:
            List of saved file info with URLs
        """
        saved_files = []

        # Create folder structure: parts/{part_number}/
        folder_prefix = f"parts/{part_number}/"

        for filename, image_bytes in image_files:
            try:
                # Full S3 key (path)
                s3_key = f"{folder_prefix}{filename}"

                # Upload to R2
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=image_bytes,
                    ContentType='image/jpeg' if filename.lower().endswith(('.jpg', '.jpeg')) else 'image/png',
                    Metadata={
                        'part_number': part_number,
                        'description': description,
                        'source': 'tescon-processor'
                    }
                )

                # Generate public URL (if bucket is public) or signed URL
                public_url = f"https://{self.bucket_name}.{self.account_id}.r2.cloudflarestorage.com/{s3_key}"

                saved_files.append({
                    'filename': filename,
                    'url': public_url,
                    's3_key': s3_key,
                    'bucket': self.bucket_name
                })

                print(f"✅ Uploaded {filename} to R2: {s3_key}")

            except Exception as e:
                print(f"❌ Failed to upload {filename}: {e}")
                raise Exception(f"Failed to upload {filename}: {str(e)}")

        return saved_files

    def check_duplicates(self, part_number: str, view_numbers: List[int]) -> Dict[int, bool]:
        """
        Check if images already exist for given part and view numbers.

        Args:
            part_number: Part number to check
            view_numbers: List of view numbers to check

        Returns:
            Dict mapping view_number -> exists (bool)
        """
        duplicates = {}
        folder_prefix = f"parts/{part_number}/"

        try:
            # List objects in the part folder
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=folder_prefix
            )

            existing_files = []
            if 'Contents' in response:
                existing_files = [obj['Key'] for obj in response['Contents']]

            # Check each view number
            for view_num in view_numbers:
                # Look for any file containing _{view_num}_
                view_exists = any(f"_{view_num}_" in filename for filename in existing_files)
                duplicates[view_num] = view_exists

        except Exception as e:
            print(f"⚠ Warning: Could not check duplicates: {e}")
            # If we can't check, assume no duplicates
            duplicates = {view_num: False for view_num in view_numbers}

        return duplicates

    def list_part_images(self, part_number: str) -> List[Dict[str, Any]]:
        """List all images for a given part number."""
        folder_prefix = f"parts/{part_number}/"
        images = []

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=folder_prefix
            )

            if 'Contents' in response:
                for obj in response['Contents']:
                    s3_key = obj['Key']
                    filename = s3_key.split('/')[-1]  # Get just the filename

                    images.append({
                        'filename': filename,
                        's3_key': s3_key,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'url': f"https://{self.bucket_name}.{self.account_id}.r2.cloudflarestorage.com/{s3_key}"
                    })

        except Exception as e:
            print(f"⚠ Warning: Could not list images for {part_number}: {e}")

        return images

    def delete_part_images(self, part_number: str) -> bool:
        """Delete all images for a given part number."""
        folder_prefix = f"parts/{part_number}/"

        try:
            # List all objects in the part folder
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=folder_prefix
            )

            if 'Contents' in response:
                # Delete all objects
                delete_keys = [{'Key': obj['Key']} for obj in response['Contents']]

                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': delete_keys}
                )

                print(f"🗑️ Deleted {len(delete_keys)} images for part {part_number}")
                return True

        except Exception as e:
            print(f"❌ Failed to delete images for {part_number}: {e}")
            return False

        return True  # No images to delete

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics."""
        try:
            # List all objects to get stats
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)

            total_objects = 0
            total_size = 0
            parts = set()

            if 'Contents' in response:
                for obj in response['Contents']:
                    total_objects += 1
                    total_size += obj['Size']

                    # Extract part number from key (parts/{part_number}/...)
                    key_parts = obj['Key'].split('/')
                    if len(key_parts) >= 2 and key_parts[0] == 'parts':
                        parts.add(key_parts[1])

            return {
                'total_objects': total_objects,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'unique_parts': len(parts),
                'bucket_name': self.bucket_name
            }

        except Exception as e:
            print(f"⚠ Warning: Could not get storage stats: {e}")
            return {
                'total_objects': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'unique_parts': 0,
                'bucket_name': self.bucket_name,
                'error': str(e)
            }


# Global instance
_r2_storage = None


def get_r2_storage() -> Optional[CloudflareR2Storage]:
    """Get or create R2 storage instance."""
    global _r2_storage

    if _r2_storage is None:
        try:
            _r2_storage = CloudflareR2Storage()
        except Exception as e:
            print(f"⚠ R2 storage not available: {e}")
            return None

    return _r2_storage


def test_r2_connection():
    """Test R2 connection and print status."""
    try:
        r2 = get_r2_storage()
        if r2:
            stats = r2.get_storage_stats()
            print(f"✅ R2 connected: {stats['total_objects']} objects, {stats['total_size_mb']} MB")
            return True
        else:
            print("❌ R2 not configured")
            return False
    except Exception as e:
        print(f"❌ R2 connection failed: {e}")
        return False