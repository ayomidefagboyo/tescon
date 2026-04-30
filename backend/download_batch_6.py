#!/usr/bin/env python3
"""
Download batch 6 of processed images.

⚠️  DEPRECATED / LEGACY: This script picks batch 6 by INDEX from the tracker API,
    which CAN overlap with already-downloaded symbols in Batches 1-5.

    For Batch 7+, use:  python batch_downloader.py download
    That uses download_state.json (local tracker) so batches never overlap.
"""

import requests
import os
import json
from pathlib import Path

def get_processed_parts():
    """Get processed parts from production API"""
    try:
        response = requests.get("https://tescon.onrender.com/api/tracker/parts/processed", timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get('processed_parts', [])
    except Exception as e:
        print(f"Error fetching processed parts: {e}")
    return []

def download_batch_6():
    """Download batch 6 (assuming 6 batches total from ~1000 parts)"""
    print("🔍 Fetching processed parts list...")
    processed_parts = get_processed_parts()

    if not processed_parts:
        print("❌ Could not fetch processed parts list")
        return

    total_parts = len(processed_parts)
    print(f"📊 Total processed parts: {total_parts}")

    # Calculate batch 6 (assuming 0-indexed, batch 6 is actually the 6th batch)
    batch_size = total_parts // 6
    batch_6_start = 5 * batch_size  # 5th index for 6th batch
    batch_6_end = min(total_parts, 6 * batch_size)

    batch_6_parts = processed_parts[batch_6_start:batch_6_end]
    print(f"📦 Batch 6: Parts {batch_6_start+1}-{batch_6_end} ({len(batch_6_parts)} parts)")

    # Create download directory
    download_dir = Path("batch_6_downloads")
    download_dir.mkdir(exist_ok=True)

    # Save batch info
    batch_info = {
        "batch_number": 6,
        "total_parts": total_parts,
        "batch_size": batch_size,
        "start_index": batch_6_start,
        "end_index": batch_6_end,
        "parts_in_batch": len(batch_6_parts),
        "part_numbers": batch_6_parts
    }

    with open(download_dir / "batch_info.json", "w") as f:
        json.dump(batch_info, f, indent=2)

    print(f"📝 Batch info saved to {download_dir}/batch_info.json")
    print(f"📋 Part numbers in batch 6:")
    for i, part in enumerate(batch_6_parts[:10]):  # Show first 10
        print(f"  {i+1}. {part}")

    if len(batch_6_parts) > 10:
        print(f"  ... and {len(batch_6_parts) - 10} more parts")

    print(f"\n💡 To download images for these parts, use:")
    print(f"python3 download_processed_images.py --output {download_dir}")

if __name__ == "__main__":
    download_batch_6()