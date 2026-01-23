#!/usr/bin/env python3
"""Test script for the new ecommerce layout with updated Excel data."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

from services.excel_service import get_excel_parts_service

def test_new_layout():
    """Test the new layout with updated Excel data."""

    # Load Excel service
    excel_service = get_excel_parts_service()

    # Load Excel file
    excel_file_path = "backend/EGTL Dump Total Dump ( sorted).xlsx"
    print("Loading Excel file...")
    success = excel_service.load_excel_file(excel_file_path, sheet_name="Data")

    if not success:
        print("❌ Failed to load Excel file")
        return False

    print("✅ Excel file loaded successfully")

    # Test a few parts to see the new data
    test_symbols = ["58018612", "58023823", "58023820"]

    for symbol in test_symbols:
        print(f"\n📋 Testing Symbol Number: {symbol}")
        part_info = excel_service.get_part_info(symbol)

        if part_info:
            print(f"  Symbol Number: {part_info.get('symbol_number')}")
            print(f"  Part Number: {part_info.get('part_number')}")
            print(f"  Manufacturer: {part_info.get('manufacturer')}")
            print(f"  Long Description: {part_info.get('long_description')[:100]}...")

            # Show what the new layout would display
            print("  New Layout Preview:")
            if part_info.get('symbol_number'):
                print(f"    1. SYMBOL NUMBER: {part_info.get('symbol_number')}")
            if part_info.get('long_description'):
                print(f"    2. LONG DESCRIPTION: {part_info.get('long_description')[:50]}...")

            part_num = part_info.get('part_number')
            manuf = part_info.get('manufacturer')
            if part_num and manuf:
                print(f"    3. PART NUMBER: {part_num}    MANUFACTURER: {manuf}")
            elif part_num:
                print(f"    3. PART NUMBER: {part_num}")
            elif manuf:
                print(f"    3. MANUFACTURER: {manuf}")

        else:
            print(f"  ❌ Part not found")

    # Show statistics
    stats = excel_service.get_stats()
    print(f"\n📊 Excel Statistics:")
    print(f"  Total parts: {stats['total_parts']}")
    print(f"  Has descriptions: {stats['has_descriptions']}")
    print(f"  Has long descriptions: {stats['has_long_descriptions']}")

    # Check how many parts have manufacturers
    if excel_service.unique_parts is not None:
        manufacturer_count = (excel_service.unique_parts['Manufacturer'] != '').sum()
        print(f"  Has manufacturers: {manufacturer_count}")

        # Show top manufacturers
        top_mfgs = excel_service.unique_parts[excel_service.unique_parts['Manufacturer'] != '']['Manufacturer'].value_counts().head(5)
        print("  Top 5 Manufacturers:")
        for mfg, count in top_mfgs.items():
            print(f"    {mfg}: {count} parts")

    return True

if __name__ == "__main__":
    test_new_layout()