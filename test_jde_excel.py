#!/usr/bin/env python3
"""Test script for the new JDE Excel file."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

from services.excel_service import get_excel_parts_service

def test_jde_excel():
    """Test the new JDE Excel file."""

    # Load Excel service
    excel_service = get_excel_parts_service()

    # Load new JDE Excel file
    excel_file_path = "backend/EGTL Dump_with_JDE.xlsx"
    print("Loading JDE Excel file...")
    success = excel_service.load_excel_file(excel_file_path, sheet_name="Data")

    if not success:
        print("❌ Failed to load JDE Excel file")
        return False

    print("✅ JDE Excel file loaded successfully")

    # Test a few parts to see the real JDE data
    test_symbols = ["58018612", "58023823", "58023820", "58023821", "58015260"]

    print("\n" + "="*60)
    print("TESTING NEW LAYOUT WITH JDE DATA")
    print("="*60)

    for symbol in test_symbols:
        print(f"\n📋 Testing Symbol Number: {symbol}")
        part_info = excel_service.get_part_info(symbol)

        if part_info:
            print(f"  Symbol Number: {part_info.get('symbol_number')}")
            print(f"  Part Number: {part_info.get('part_number')}")
            print(f"  Manufacturer: {part_info.get('manufacturer')}")
            print(f"  Long Description: {part_info.get('long_description', '')[:80]}...")

            # Show what the new layout would display on the image
            print("  🖼️  IMAGE LAYOUT PREVIEW:")
            if part_info.get('symbol_number'):
                print(f"    1. SYMBOL NUMBER: {part_info.get('symbol_number')}")
            if part_info.get('long_description'):
                long_desc = part_info.get('long_description', '')
                print(f"    2. LONG DESCRIPTION: {long_desc[:60]}{'...' if len(long_desc) > 60 else ''}")

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

    # Show overall statistics
    stats = excel_service.get_stats()
    print(f"\n📊 JDE EXCEL STATISTICS:")
    print(f"  Total parts: {stats['total_parts']:,}")
    print(f"  Has descriptions: {stats['has_descriptions']:,}")
    print(f"  Has long descriptions: {stats['has_long_descriptions']:,}")

    # Check JDE-specific data
    if excel_service.unique_parts is not None:
        part_no_count = excel_service.unique_parts['Part No'].notna().sum()
        mfg_name_count = excel_service.unique_parts['Mfg Name'].notna().sum()

        print(f"  Has Part Numbers (JDE): {part_no_count:,}")
        print(f"  Has Manufacturers (JDE): {mfg_name_count:,}")

        # Show top manufacturers from JDE data
        print(f"\n🏭 TOP 10 MANUFACTURERS (from JDE):")
        top_mfgs = excel_service.unique_parts[excel_service.unique_parts['Mfg Name'].notna()]['Mfg Name'].value_counts().head(10)
        for i, (mfg, count) in enumerate(top_mfgs.items(), 1):
            print(f"  {i:2}. {mfg}: {count:,} parts")

        # Show sample part numbers
        print(f"\n🔢 SAMPLE PART NUMBERS:")
        sample_parts = excel_service.unique_parts[excel_service.unique_parts['Part No'].notna()]['Part No'].head(5)
        for i, part_no in enumerate(sample_parts, 1):
            print(f"  {i}. {part_no}")

    print("\n✅ JDE Excel file testing completed!")
    return True

if __name__ == "__main__":
    test_jde_excel()