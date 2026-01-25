#!/usr/bin/env python3
"""Test Excel file loading without R2 dependencies."""

import sys
import os
sys.path.append('app')

def test_excel_loading():
    print("🔍 Testing Excel file loading...")

    try:
        from services.excel_service import get_excel_parts_service

        excel_service = get_excel_parts_service()
        print("✅ Excel service initialized")

        # Test loading the new Excel file
        print("📂 Loading egtl_cleaned_OPTIMIZED_20260124_131513.xlsx...")
        success = excel_service.load_excel_file('egtl_filtered_clean.xlsx', sheet_name='DATA')

        if success:
            stats = excel_service.get_stats()
            print(f"✅ Successfully loaded: {stats['total_parts']} parts")
            print(f"   Parts with descriptions: {stats['has_descriptions']}")
            print(f"   Parts with long descriptions: {stats['has_long_descriptions']}")

            # Test a few symbol lookups
            print("\n🔍 Testing symbol lookups:")
            test_symbols = ['2531868', 'TEST567', '87731598']
            for symbol in test_symbols:
                part = excel_service.get_part_info(symbol)
                if part:
                    print(f"  ✅ {symbol}: Found - {part.get('description_1', 'No description')}")
                else:
                    print(f"  ❌ {symbol}: Not found")
        else:
            print("❌ Failed to load Excel file")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_excel_loading()