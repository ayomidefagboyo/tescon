#!/usr/bin/env python3
"""
Incremental batch downloader for R2 processed parts.
Only downloads new parts that haven't been downloaded before.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Set, List, Dict, Any

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.cloudflare_r2 import get_r2_storage

class BatchDownloader:
    def __init__(self, download_base_dir: str = None):
        """Initialize batch downloader."""
        if download_base_dir is None:
            self.download_base_dir = Path(__file__).parent / "downloads"
        else:
            self.download_base_dir = Path(download_base_dir)

        self.download_base_dir.mkdir(parents=True, exist_ok=True)

        # State tracking file
        self.state_file = self.download_base_dir / "download_state.json"
        self.state = self._load_state()

        # R2 connection
        self.r2 = get_r2_storage()
        if not self.r2:
            raise Exception("Could not connect to R2 storage")

    def _load_state(self) -> Dict[str, Any]:
        """Load download state from file."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)

        return {
            "downloaded_parts": [],
            "last_download": None,
            "batch_count": 0
        }

    def _save_state(self):
        """Save download state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def get_all_r2_parts(self) -> Set[str]:
        """Get all part numbers currently in R2 storage."""
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
            print(f"❌ Error getting R2 parts: {e}")
            return set()

        return parts

    def get_new_parts(self) -> Set[str]:
        """Get parts that haven't been downloaded yet."""
        all_parts = self.get_all_r2_parts()
        downloaded_parts = set(self.state["downloaded_parts"])

        new_parts = all_parts - downloaded_parts
        return new_parts

    def download_part(self, symbol_number: str, batch_dir: Path) -> bool:
        """Download all images for a specific part."""
        try:
            # Create part folder
            part_dir = batch_dir / symbol_number
            part_dir.mkdir(exist_ok=True)

            # Get part images from R2
            images = self.r2.list_part_images(symbol_number)

            if not images:
                print(f"⚠ No images found for part {symbol_number}")
                return False

            downloaded_count = 0
            for image_info in images:
                try:
                    # Download image
                    response = self.r2.s3_client.get_object(
                        Bucket=self.r2.bucket_name,
                        Key=image_info['s3_key']
                    )

                    # Save to local file
                    local_file = part_dir / image_info['filename']
                    with open(local_file, 'wb') as f:
                        f.write(response['Body'].read())

                    downloaded_count += 1

                except Exception as e:
                    print(f"❌ Failed to download {image_info['filename']}: {e}")

            if downloaded_count > 0:
                print(f"✅ Downloaded {downloaded_count} images for part {symbol_number}")
                return True
            else:
                print(f"❌ No images downloaded for part {symbol_number}")
                return False

        except Exception as e:
            print(f"❌ Error downloading part {symbol_number}: {e}")
            return False

    def run_batch_download(self, max_parts: int = None) -> Dict[str, Any]:
        """Run a batch download of new parts."""
        new_parts = self.get_new_parts()

        if not new_parts:
            return {
                "status": "no_new_parts",
                "message": "No new parts to download",
                "downloaded": 0
            }

        # Limit batch size if specified
        if max_parts:
            new_parts = set(sorted(new_parts)[:max_parts])

        # Create batch folder
        self.state["batch_count"] += 1
        today = datetime.now().strftime("%Y%m%d")
        batch_name = f"Batch_{self.state['batch_count']}_{today}"
        batch_dir = self.download_base_dir / batch_name
        batch_dir.mkdir(exist_ok=True)

        print(f"📁 Starting {batch_name}")
        print(f"📁 Downloading to: {batch_dir}")
        print(f"🔄 Processing {len(new_parts)} new parts...")

        # Download parts
        successful_downloads = []
        failed_downloads = []

        for i, part_number in enumerate(sorted(new_parts), 1):
            print(f"\n[{i}/{len(new_parts)}] Downloading part {part_number}...")

            if self.download_part(part_number, batch_dir):
                successful_downloads.append(part_number)
            else:
                failed_downloads.append(part_number)

        # Update state
        self.state["downloaded_parts"].extend(successful_downloads)
        self.state["last_download"] = datetime.now().isoformat()
        self._save_state()

        # Create batch summary
        summary = {
            "batch_name": batch_name,
            "download_date": datetime.now().isoformat(),
            "parts_attempted": len(new_parts),
            "parts_successful": len(successful_downloads),
            "parts_failed": len(failed_downloads),
            "successful_parts": successful_downloads,
            "failed_parts": failed_downloads
        }

        # Save batch summary
        summary_file = batch_dir / "batch_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        return {
            "status": "completed",
            "batch_dir": str(batch_dir),
            "summary": summary
        }

    def show_status(self):
        """Show current download status."""
        all_parts = self.get_all_r2_parts()
        downloaded_parts = set(self.state["downloaded_parts"])
        new_parts = self.get_new_parts()

        print(f"\n📊 Download Status:")
        print(f"   Total parts in R2: {len(all_parts)}")
        print(f"   Already downloaded: {len(downloaded_parts)}")
        print(f"   New parts available: {len(new_parts)}")
        print(f"   Batches completed: {self.state['batch_count']}")
        print(f"   Last download: {self.state.get('last_download', 'Never')}")
        print(f"   Download location: {self.download_base_dir}")

        if new_parts:
            print(f"\n🆕 New parts to download: {sorted(list(new_parts))[:10]}{'...' if len(new_parts) > 10 else ''}")


def main():
    """Main function."""
    print("🚀 Tescon Batch Downloader")
    print("=" * 50)

    # Load environment
    env_file = Path(__file__).parent / "backend" / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    try:
        downloader = BatchDownloader()

        if len(sys.argv) > 1:
            command = sys.argv[1].lower()

            if command == "status":
                downloader.show_status()

            elif command == "download":
                # Optional batch size limit
                max_parts = None
                if len(sys.argv) > 2:
                    try:
                        max_parts = int(sys.argv[2])
                        print(f"📏 Limiting batch to {max_parts} parts")
                    except ValueError:
                        print(f"⚠ Invalid batch size: {sys.argv[2]}")

                result = downloader.run_batch_download(max_parts)

                if result["status"] == "no_new_parts":
                    print("✅ All parts already downloaded!")
                elif result["status"] == "completed":
                    summary = result["summary"]
                    print(f"\n✅ Batch download completed!")
                    print(f"📁 Location: {result['batch_dir']}")
                    print(f"📊 Downloaded: {summary['parts_successful']}/{summary['parts_attempted']} parts")
                    if summary['failed_parts']:
                        print(f"❌ Failed: {summary['failed_parts']}")

            else:
                print(f"❌ Unknown command: {command}")
                print("Usage: python batch_downloader.py [status|download] [max_parts]")

        else:
            # Default: show status
            downloader.show_status()
            print(f"\nUsage:")
            print(f"  python {sys.argv[0]} status           - Show download status")
            print(f"  python {sys.argv[0]} download         - Download all new parts")
            print(f"  python {sys.argv[0]} download 30      - Download max 30 new parts")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())