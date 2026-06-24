#!/usr/bin/env python3
"""
Manual script to sync parts_tracker.json with actual R2 storage state.

This fixes tracker accuracy by scanning R2 and updating the tracker to match reality.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.cloudflare_r2 import get_r2_storage
from app.services.parts_tracker import get_parts_tracker
from app.services.excel_service import get_excel_parts_service

def sync_tracker():
    """Sync tracker with R2 storage."""
    
    print("🔄 TRACKER SYNC UTILITY")
    print("=" * 60)
    
    # Initialize services
    tracker = get_parts_tracker()
    r2_storage = get_r2_storage()
    excel_service = get_excel_parts_service()
    
    if not r2_storage:
        print("❌ R2 storage not configured")
        print("   Set environment variables: R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET")
        return False
    
    # Load Excel file if exists
    excel_files = list(Path('.').glob('*.xlsx'))
    if excel_files:
        excel_file = excel_files[0]
        print(f"📊 Loading Excel file: {excel_file}")
        excel_service.load_excel_file(str(excel_file))
        stats = excel_service.get_stats()
        print(f"   Loaded {stats['total_parts']} parts from catalog")
        
        # Update total parts in tracker
        tracker.set_total_parts(stats['total_parts'])
    else:
        print("⚠️  No Excel file found, skipping total parts update")
    
    # Scan R2 storage
    print("\n🔍 Scanning R2 storage...")
    
    processed_parts = set()
    queued_parts = set()
    
    # Check processed parts (parts/ folder)
    print("   Checking parts/ folder...")
    paginator = r2_storage.s3_client.get_paginator('list_objects_v2')
    
    for page in paginator.paginate(Bucket=r2_storage.bucket_name, Prefix='parts/'):
        for obj in page.get('Contents', []):
            key = obj['Key']
            # Extract symbol number from path: parts/SYMBOL/filename
            parts_path = key.split('/')
            if len(parts_path) >= 2:
                symbol_number = parts_path[1]
                processed_parts.add(symbol_number)
    
    print(f"   ✅ Found {len(processed_parts)} processed parts")
    
    # Check queued parts (raw/ folder)
    print("   Checking raw/ folder...")
    for page in paginator.paginate(Bucket=r2_storage.bucket_name, Prefix='raw/'):
        for obj in page.get('Contents', []):
            key = obj['Key']
            # Extract symbol number from path: raw/SYMBOL/filename
            parts_path = key.split('/')
            if len(parts_path) >= 2:
                symbol_number = parts_path[1]
                # Only mark as queued if not already processed
                if symbol_number not in processed_parts:
                    queued_parts.add(symbol_number)
    
    print(f"   ✅ Found {len(queued_parts)} queued parts")
    
    # Update tracker
    print("\n📝 Updating tracker...")
    
    # Clear current state
    tracker.processed_parts.clear()
    tracker.queued_parts.clear()
    tracker.failed_parts.clear()
    tracker.part_stats.clear()
    
    # Add processed parts
    for symbol_number in processed_parts:
        # Count images for this part
        prefix = f"parts/{symbol_number}/"
        response = r2_storage.s3_client.list_objects_v2(
            Bucket=r2_storage.bucket_name,
            Prefix=prefix
        )
        image_count = len(response.get('Contents', []))
        tracker.mark_part_processed(symbol_number, image_count)
    
    print(f"   ✅ Marked {len(processed_parts)} parts as processed")
    
    # Add queued parts
    for symbol_number in queued_parts:
        # Count raw images
        prefix = f"raw/{symbol_number}/"
        response = r2_storage.s3_client.list_objects_v2(
            Bucket=r2_storage.bucket_name,
            Prefix=prefix
        )
        image_count = len(response.get('Contents', []))
        tracker.mark_part_queued(symbol_number, image_count)
    
    print(f"   ✅ Marked {len(queued_parts)} parts as queued")
    
    # Save tracker
    tracker.save_tracker()
    
    # Display final stats
    print("\n📊 FINAL TRACKER STATS")
    print("=" * 60)
    stats = tracker.get_progress_stats()
    
    print(f"Total Parts:     {stats['total_parts']:,}")
    print(f"Processed:       {stats['processed_count']:,} ({stats['progress_percentage']:.1f}%)")
    print(f"Queued:          {stats['queued_count']:,}")
    print(f"Failed:          {stats['failed_count']:,}")
    print(f"Remaining:       {stats['remaining_count']:,}")
    print(f"Success Rate:    {stats['success_rate']:.1f}%")
    
    print("\n✅ Tracker sync complete!")
    print(f"   Tracker file: {tracker.tracker_file}")
    
    return True

if __name__ == "__main__":
    try:
        success = sync_tracker()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
