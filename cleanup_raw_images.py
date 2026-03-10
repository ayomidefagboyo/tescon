#!/usr/bin/env python3
"""
Cleanup script to delete raw images for parts that have been processed.
Only deletes raw images if corresponding processed images exist in parts/ folder.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Set, List, Dict, Any

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.cloudflare_r2 import get_r2_storage


class RawImageCleanup:
    def __init__(self):
        """Initialize cleanup utility."""
        self.r2 = get_r2_storage()
        if not self.r2:
            raise Exception("Could not connect to R2 storage")

    def get_processed_parts(self) -> Set[str]:
        """Get all part numbers that have processed images."""
        parts = set()

        try:
            response = self.r2.s3_client.list_objects_v2(
                Bucket=self.r2.bucket_name,
                Prefix="parts/",
                Delimiter="/"
            )

            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    part_number = prefix['Prefix'].replace('parts/', '').rstrip('/')
                    if part_number:
                        parts.add(part_number)

        except Exception as e:
            print(f"❌ Error getting processed parts: {e}")
            return set()

        return parts

    def get_raw_parts(self) -> Set[str]:
        """Get all part numbers that have raw images."""
        parts = set()

        try:
            response = self.r2.s3_client.list_objects_v2(
                Bucket=self.r2.bucket_name,
                Prefix="raw/",
                Delimiter="/"
            )

            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    part_number = prefix['Prefix'].replace('raw/', '').rstrip('/')
                    if part_number:
                        parts.add(part_number)

        except Exception as e:
            print(f"❌ Error getting raw parts: {e}")
            return set()

        return parts

    def verify_safe_to_delete(self, part_number: str) -> bool:
        """Verify that a part has processed images before deleting raw images."""
        try:
            # Check if processed images exist
            parts_response = self.r2.s3_client.list_objects_v2(
                Bucket=self.r2.bucket_name,
                Prefix=f"parts/{part_number}/"
            )

            processed_count = len(parts_response.get('Contents', []))

            if processed_count >= 3:  # Expect at least 3 processed images
                return True
            else:
                print(f"⚠ Warning: Part {part_number} has only {processed_count} processed images")
                return False

        except Exception as e:
            print(f"❌ Error verifying part {part_number}: {e}")
            return False

    def delete_raw_images_for_part(self, part_number: str) -> bool:
        """Delete all raw images for a specific part."""
        try:
            # List all raw images for this part
            response = self.r2.s3_client.list_objects_v2(
                Bucket=self.r2.bucket_name,
                Prefix=f"raw/{part_number}/"
            )

            if 'Contents' not in response:
                print(f"ℹ No raw images found for part {part_number}")
                return True

            # Delete all raw images
            delete_keys = [{'Key': obj['Key']} for obj in response['Contents']]

            if delete_keys:
                self.r2.s3_client.delete_objects(
                    Bucket=self.r2.bucket_name,
                    Delete={'Objects': delete_keys}
                )

                print(f"🗑️ Deleted {len(delete_keys)} raw images for part {part_number}")
                return True

        except Exception as e:
            print(f"❌ Failed to delete raw images for {part_number}: {e}")
            return False

        return True

    def cleanup_raw_images(self, test_mode: bool = True, max_parts: int = None) -> Dict[str, Any]:
        """Clean up raw images for processed parts."""
        processed_parts = self.get_processed_parts()
        raw_parts = self.get_raw_parts()

        # Find parts that have both raw and processed images
        parts_to_cleanup = processed_parts & raw_parts

        if not parts_to_cleanup:
            return {
                "status": "no_cleanup_needed",
                "message": "No raw images need cleanup",
                "cleaned": 0
            }

        if max_parts:
            parts_to_cleanup = set(sorted(parts_to_cleanup)[:max_parts])

        print(f"🧹 Raw Image Cleanup {'(TEST MODE)' if test_mode else ''}")
        print(f"📊 Found {len(processed_parts)} processed parts")
        print(f"📊 Found {len(raw_parts)} raw parts")
        print(f"🎯 Targeting {len(parts_to_cleanup)} parts for cleanup")

        if test_mode:
            print(f"🔍 TEST MODE - Would clean: {sorted(list(parts_to_cleanup))[:10]}{'...' if len(parts_to_cleanup) > 10 else ''}")
            return {
                "status": "test_mode",
                "parts_to_cleanup": len(parts_to_cleanup),
                "sample_parts": sorted(list(parts_to_cleanup))[:10]
            }

        # Actually delete raw images
        successful_cleanups = []
        failed_cleanups = []

        for i, part_number in enumerate(sorted(parts_to_cleanup), 1):
            print(f"\n[{i}/{len(parts_to_cleanup)}] Cleaning part {part_number}...")

            # Verify it's safe to delete
            if not self.verify_safe_to_delete(part_number):
                print(f"⚠ Skipping {part_number} - not safe to delete")
                failed_cleanups.append(part_number)
                continue

            if self.delete_raw_images_for_part(part_number):
                successful_cleanups.append(part_number)
            else:
                failed_cleanups.append(part_number)

        return {
            "status": "completed",
            "cleaned_parts": len(successful_cleanups),
            "failed_parts": len(failed_cleanups),
            "successful_cleanups": successful_cleanups,
            "failed_cleanups": failed_cleanups,
            "cleanup_date": datetime.now().isoformat()
        }

    def get_storage_savings_estimate(self) -> Dict[str, Any]:
        """Estimate storage savings from cleanup."""
        try:
            # Get size of raw images
            response = self.r2.s3_client.list_objects_v2(
                Bucket=self.r2.bucket_name,
                Prefix="raw/"
            )

            total_raw_size = 0
            total_raw_count = 0

            if 'Contents' in response:
                for obj in response['Contents']:
                    total_raw_size += obj['Size']
                    total_raw_count += 1

            return {
                "total_raw_files": total_raw_count,
                "total_raw_size_bytes": total_raw_size,
                "total_raw_size_mb": round(total_raw_size / 1024 / 1024, 2),
                "total_raw_size_gb": round(total_raw_size / 1024 / 1024 / 1024, 2)
            }

        except Exception as e:
            print(f"⚠ Error estimating savings: {e}")
            return {"error": str(e)}


def main():
    """Main function."""
    print("🧹 Tescon Raw Image Cleanup")
    print("=" * 50)

    # Load environment
    env_file = Path(__file__).parent / "backend" / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    try:
        cleanup = RawImageCleanup()

        if len(sys.argv) > 1:
            command = sys.argv[1].lower()

            if command == "estimate":
                savings = cleanup.get_storage_savings_estimate()
                if 'error' not in savings:
                    print(f"💾 Storage Estimate:")
                    print(f"   Raw files: {savings['total_raw_files']}")
                    print(f"   Raw size: {savings['total_raw_size_gb']:.2f} GB")
                    print(f"   Potential savings: ~{savings['total_raw_size_gb']:.2f} GB")

            elif command == "test":
                # Test mode - show what would be cleaned
                max_parts = None
                if len(sys.argv) > 2:
                    try:
                        max_parts = int(sys.argv[2])
                    except ValueError:
                        print(f"⚠ Invalid max_parts: {sys.argv[2]}")

                result = cleanup.cleanup_raw_images(test_mode=True, max_parts=max_parts)
                print(f"\n📋 Test Results:")
                print(f"   Parts to cleanup: {result.get('parts_to_cleanup', 0)}")

            elif command == "cleanup":
                # Actual cleanup
                max_parts = None
                force = False

                for arg in sys.argv[2:]:
                    if arg == "--force":
                        force = True
                    else:
                        try:
                            max_parts = int(arg)
                            print(f"📏 Limiting cleanup to {max_parts} parts")
                        except ValueError:
                            print(f"⚠ Invalid argument: {arg}")

                if not force:
                    confirm = input(f"⚠ This will permanently delete raw images. Continue? (y/N): ")
                    if confirm.lower() != 'y':
                        print("❌ Cleanup cancelled")
                        return 1

                result = cleanup.cleanup_raw_images(test_mode=False, max_parts=max_parts)

                if result["status"] == "completed":
                    print(f"\n✅ Cleanup completed!")
                    print(f"🗑️ Cleaned: {result['cleaned_parts']} parts")
                    print(f"❌ Failed: {result['failed_parts']} parts")

                    if result['failed_cleanups']:
                        print(f"Failed parts: {result['failed_cleanups']}")

            else:
                print(f"❌ Unknown command: {command}")
                print("Usage:")
                print(f"  python {sys.argv[0]} estimate        - Show storage savings estimate")
                print(f"  python {sys.argv[0]} test [max]      - Test mode (show what would be cleaned)")
                print(f"  python {sys.argv[0]} cleanup [max]   - Actually clean raw images")

        else:
            # Default: show estimate
            print("Usage:")
            print(f"  python {sys.argv[0]} estimate        - Show storage savings estimate")
            print(f"  python {sys.argv[0]} test [max]      - Test mode (show what would be cleaned)")
            print(f"  python {sys.argv[0]} cleanup [max]   - Actually clean raw images")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())