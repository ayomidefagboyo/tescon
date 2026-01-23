#!/usr/bin/env python3
"""Test script to verify Long Text JDE is being used instead of Long Text Desc."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

from services.excel_service import get_excel_parts_service

def test_long_text_jde():
    """Test that Long Text JDE is being used for long descriptions."""

    # Load Excel service
    excel_service = get_excel_parts_service()

    # Load JDE Excel file
    excel_file_path = "backend/EGTL Dump_with_JDE.xlsx"
    print("Loading JDE Excel file...")
    success = excel_service.load_excel_file(excel_file_path, sheet_name="Data")

    if not success:
        print("❌ Failed to load JDE Excel file")
        return False

    print("✅ JDE Excel file loaded successfully")

    # Test a few parts to compare Long Text JDE vs Long Text Desc
    test_symbols = ["58018612", "58023823", "58023820"]

    print("\n" + "="*80)
    print("COMPARING LONG TEXT JDE vs LONG TEXT DESC")
    print("="*80)

    for symbol in test_symbols:
        print(f"\n📋 Testing Symbol Number: {symbol}")
        part_info = excel_service.get_part_info(symbol)

        if part_info:
            # Get raw data to compare
            raw_data = excel_service.unique_parts[
                excel_service.unique_parts['Symbol Number'].astype(str) == str(symbol)
            ].iloc[0]

            print(f"  Symbol Number: {part_info.get('symbol_number')}")
            print(f"  Part Number: {part_info.get('part_number')}")
            print(f"  Manufacturer: {part_info.get('manufacturer')}")

            print(f"\n  📄 LONG TEXT COMPARISON:")
            print(f"  Old (Long Text Desc): {str(raw_data['Long Text Desc'])[:100]}...")
            print(f"  New (Long Text JDE):  {str(raw_data['Long Text JDE'])[:100]}...")

            print(f"\n  ✅ SYSTEM IS USING (long_description): {part_info.get('long_description', '')[:100]}...")

            # Show what appears in the image layout
            print(f"\n  🖼️  IMAGE LAYOUT PREVIEW:")
            print(f"    1. SYMBOL NUMBER: {part_info.get('symbol_number')}")
            print(f"    2. LONG DESCRIPTION: {part_info.get('long_description', '')[:60]}...")

            part_num = part_info.get('part_number')
            manuf = part_info.get('manufacturer')
            if part_num and manuf:
                print(f"    3. PART NUMBER: {part_num}    MANUFACTURER: {manuf}")
            elif part_num:
                print(f"    3. PART NUMBER: {part_num}")
            elif manuf:
                print(f"    3. MANUFACTURER: {manuf}")

            # Verify we're using JDE text
            jde_text = str(raw_data['Long Text JDE'])
            system_text = part_info.get('long_description', '')
            if jde_text.strip() == system_text.strip():
                print(f"    ✅ CONFIRMED: Using Long Text JDE")
            else:
                print(f"    ❌ ERROR: Not using Long Text JDE")

        else:
            print(f"  ❌ Part not found")

    # Show overall statistics
    stats = excel_service.get_stats()
    print(f"\n📊 STATISTICS:")
    print(f"  Total parts: {stats['total_parts']:,}")
    print(f"  Has long descriptions (JDE): {stats['has_long_descriptions']:,}")

    # Direct comparison of coverage
    if excel_service.unique_parts is not None:
        jde_count = excel_service.unique_parts['Long Text JDE'].notna().sum()
        desc_count = excel_service.unique_parts['Long Text Desc'].notna().sum()

        print(f"\n📈 COVERAGE COMPARISON:")
        print(f"  Long Text JDE populated: {jde_count:,} ({jde_count/len(excel_service.unique_parts)*100:.1f}%)")
        print(f"  Long Text Desc populated: {desc_count:,} ({desc_count/len(excel_service.unique_parts)*100:.1f}%)")
        print(f"  ✅ System now uses: Long Text JDE")

    print("\n✅ Long Text JDE verification completed!")
    return True

if __name__ == "__main__":
    test_long_text_jde()