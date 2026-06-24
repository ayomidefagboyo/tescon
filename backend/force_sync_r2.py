import sys, os, asyncio, json
from datetime import datetime

# Load env
from dotenv import load_dotenv
load_dotenv('backend/.env')

backend_root = os.path.dirname(os.path.abspath('backend/app/api/routes.py'))
sys.path.insert(0, 'backend')

from app.services.parts_tracker import get_parts_tracker
from app.services.cloudflare_r2 import get_r2_storage

def sync_r2_to_db():
    tracker = get_parts_tracker()
    tracker.refresh_from_db()
    r2_storage = get_r2_storage()
    
    if not r2_storage:
        print("R2 storage not available")
        return
        
    processed_parts = set()
    queued_parts = set()
    processed_image_counts = {}
    queued_image_counts = {}
    parts_with_timestamps = {}
    
    print("🔄 Scanning R2 storage...")
    paginator = r2_storage.s3_client.get_paginator('list_objects_v2')
    
    # Processed
    for page in paginator.paginate(Bucket=r2_storage.bucket_name, Prefix='parts/'):
        for obj in page.get('Contents', []):
            key = obj.get('Key', '')
            if not key or key.endswith('/'): continue
            parts_path = key.split('/')
            if len(parts_path) < 3: continue
            symbol_number = (parts_path[1] or '').strip()
            if not symbol_number: continue
            
            processed_parts.add(symbol_number)
            processed_image_counts[symbol_number] = processed_image_counts.get(symbol_number, 0) + 1
            
            last_modified = obj.get('LastModified')
            if last_modified and (
                symbol_number not in parts_with_timestamps or
                last_modified < parts_with_timestamps[symbol_number]
            ):
                parts_with_timestamps[symbol_number] = last_modified

    # Queued
    for page in paginator.paginate(Bucket=r2_storage.bucket_name, Prefix='raw/'):
        for obj in page.get('Contents', []):
            key = obj.get('Key', '')
            if not key or key.endswith('/'): continue
            parts_path = key.split('/')
            if len(parts_path) < 3: continue
            symbol_number = (parts_path[1] or '').strip()
            if not symbol_number or symbol_number in processed_parts: continue
            
            queued_parts.add(symbol_number)
            queued_image_counts[symbol_number] = queued_image_counts.get(symbol_number, 0) + 1
            
    print(f"📊 Found {len(processed_parts)} processed, {len(queued_parts)} queued")
    
    previous_stats = tracker.part_stats.copy()
    now_iso = datetime.now().isoformat()
    rebuilt_part_stats = {}
    
    for symbol_number in processed_parts:
        previous = previous_stats.get(symbol_number, {})
        if previous.get('status') == 'completed' and previous.get('completed_at'):
            completed_at = previous['completed_at']
        elif symbol_number in parts_with_timestamps:
            r2_timestamp = parts_with_timestamps[symbol_number]
            completed_at = r2_timestamp.isoformat() if hasattr(r2_timestamp, 'isoformat') else r2_timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f')
        else:
            completed_at = now_iso
            
        rebuilt_part_stats[symbol_number] = {
            'status': 'completed',
            'image_count': processed_image_counts.get(symbol_number, 0),
            'processing_time': previous.get('processing_time'),
            'completed_at': completed_at
        }
        
    for symbol_number in queued_parts:
        previous = previous_stats.get(symbol_number, {})
        queued_at = previous.get('queued_at') if previous.get('status') == 'queued' and previous.get('queued_at') else now_iso
        rebuilt_part_stats[symbol_number] = {
            'status': 'queued',
            'image_count': queued_image_counts.get(symbol_number, 0),
            'queued_at': queued_at
        }
        
    tracker.replace_state(
        processed_parts=processed_parts,
        queued_parts=queued_parts,
        failed_parts={},
        part_stats=rebuilt_part_stats,
        total_parts=4000 # dummy since we don't load excel
    )
    print("Done replacing state in SQLite.")

sync_r2_to_db()
