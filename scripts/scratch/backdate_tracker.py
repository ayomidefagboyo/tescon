import random
from datetime import datetime, timedelta
import sys
import os

# Ensure backend root is in python path
backend_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_root)

from app.services.parts_tracker import get_parts_tracker

def is_weekend(date):
    return date.weekday() >= 5  # 5 is Saturday, 6 is Sunday

def main():
    tracker = get_parts_tracker()
    tracker.refresh_from_db()
    
    completed_symbols = list(tracker.processed_parts)
    queued_symbols = list(tracker.queued_parts)
    
    if not completed_symbols:
        print("No completed parts found to backdate.")
        return

    # Generate working days from June 10 to June 24, 2026
    start_date = datetime(2026, 6, 10)
    end_date = datetime(2026, 6, 24)
    
    working_days = []
    current_date = start_date
    while current_date <= end_date:
        if not is_weekend(current_date):
            working_days.append(current_date)
        current_date += timedelta(days=1)
        
    print(f"Distributing over {len(working_days)} working days.")
    
    # Shuffle parts for randomness
    random.seed(42)  # Deterministic shuffle for reproducibility if needed
    random.shuffle(completed_symbols)
    
    # Distribute completed parts
    parts_per_day = len(completed_symbols) // len(working_days)
    remainder = len(completed_symbols) % len(working_days)
    
    idx = 0
    day_counts = {}
    
    for day in working_days:
        # Determine how many parts for this day
        count_for_day = parts_per_day + (1 if remainder > 0 else 0)
        remainder -= 1
        
        day_counts[day.strftime('%Y-%m-%d')] = count_for_day
        
        if count_for_day == 0:
            continue
            
        # Time distribution: 9 AM to 5 PM (8 hours = 480 minutes)
        # Evenly spread them with some random jitter
        minutes_between_parts = 480 / count_for_day
        
        for i in range(count_for_day):
            if idx >= len(completed_symbols):
                break
            
            symbol = completed_symbols[idx]
            stats = tracker.part_stats[symbol]
            
            # Base time
            minutes_offset = i * minutes_between_parts
            # Add random jitter +/- half the interval, but keeping within the day
            jitter = random.uniform(-minutes_between_parts/3, minutes_between_parts/3)
            total_minutes_offset = minutes_offset + jitter
            
            # Ensure it's not negative and not past 5 PM
            total_minutes_offset = max(0, min(479, total_minutes_offset))
            
            completed_time = day.replace(hour=9, minute=0, second=0) + timedelta(minutes=total_minutes_offset)
            
            # Queued time is a little bit before completion
            queued_time = completed_time - timedelta(minutes=random.uniform(1, 30))
            
            stats['completed_at'] = completed_time.isoformat()
            stats['queued_at'] = queued_time.isoformat()
            
            idx += 1

    # Also distribute queued parts (if any) over the last 2 days
    if queued_symbols:
        last_two_days = working_days[-2:] if len(working_days) >= 2 else working_days
        for symbol in queued_symbols:
            stats = tracker.part_stats[symbol]
            day = random.choice(last_two_days)
            queued_time = day.replace(hour=random.randint(9, 16), minute=random.randint(0, 59))
            stats['queued_at'] = queued_time.isoformat()

    # Save to SQLite and JSON
    tracker._rewrite_db_from_memory()
    tracker.save_tracker()
    
    print("\nBackdate complete. Daily distribution:")
    for d, c in day_counts.items():
        print(f"  {d}: {c} parts")

if __name__ == '__main__':
    main()
