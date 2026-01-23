#!/usr/bin/env python3
"""Test script to verify the fallback mechanism for Long Text JDE."""

import sys
import os
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

from services.excel_service import get_excel_parts_service

def test_fallback():
    """Test the fallback mechanism when Long Text JDE is empty."""

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

    # Find parts with empty Long Text JDE to test fallback
    df = excel_service.unique_parts
    jde_empty = df['Long Text JDE'].isna() | (df['Long Text JDE'] == '') | (df['Long Text JDE'].astype(str) == 'nan')
    fallback_parts = df[jde_empty].head(5)

    print("\n" + "="*80)
    print("TESTING FALLBACK MECHANISM")
    print("="*80)

    for _, row in fallback_parts.iterrows():
        symbol = str(row['Symbol Number'])
        print(f"\n📋 Testing Symbol Number: {symbol}")

        # Get part info through the service (which should use fallback)
        part_info = excel_service.get_part_info(symbol)

        if part_info:
            print(f"  Symbol Number: {part_info.get('symbol_number')}")
            print(f"  Part Number: {part_info.get('part_number')}")
            print(f"  Manufacturer: {part_info.get('manufacturer')}")

            # Show raw data
            print(f"\n  📄 RAW DATA:")
            print(f"    Long Text JDE: '{row['Long Text JDE']}'")
            print(f"    Desc1: '{row['Desc1']}'")
            print(f"    Desc2: '{row['Desc2']}'")

            # Show what the system returns
            long_desc = part_info.get('long_description', '')
            print(f"\n  🔄 FALLBACK RESULT:")
            print(f"    long_description: '{long_desc}'")

            # Verify fallback logic
            desc1 = str(row['Desc1']) if pd.notna(row['Desc1']) else ''
            desc2 = str(row['Desc2']) if pd.notna(row['Desc2']) else ''
            expected_fallback = ' | '.join(filter(None, [desc1.strip(), desc2.strip()]))

            if long_desc == expected_fallback:
                print(f"    ✅ FALLBACK WORKING: Using Desc1 + Desc2")
            else:
                print(f"    ❌ FALLBACK ERROR: Expected '{expected_fallback}'")

            # Show what appears in image layout
            print(f"\n  🖼️  IMAGE LAYOUT PREVIEW:")
            print(f"    1. SYMBOL NUMBER: {part_info.get('symbol_number')}")
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

    # Test a part WITH Long Text JDE to ensure it's not affected
    jde_available = df[~jde_empty].head(2)
    print(f"\n📊 TESTING PARTS WITH JDE DATA (should NOT use fallback):")

    for _, row in jde_available.iterrows():
        symbol = str(row['Symbol Number'])
        part_info = excel_service.get_part_info(symbol)
        if part_info:
            jde_desc = str(row['Long Text JDE'])
            system_desc = part_info.get('long_description', '')
            if jde_desc.strip() == system_desc.strip():
                print(f"  ✅ {symbol}: Using Long Text JDE (no fallback)")
            else:
                print(f"  ❌ {symbol}: Fallback incorrectly triggered")

    # Show overall statistics
    import pandas as pd
    jde_empty_count = (df['Long Text JDE'].isna() | (df['Long Text JDE'] == '') | (df['Long Text JDE'].astype(str) == 'nan')).sum()
    total_count = len(df)

    print(f"\n📊 FALLBACK STATISTICS:")
    print(f"  Total parts: {total_count:,}")
    print(f"  Parts using fallback: {jde_empty_count:,} ({jde_empty_count/total_count*100:.1f}%)")
    print(f"  Parts using Long Text JDE: {total_count - jde_empty_count:,} ({(total_count - jde_empty_count)/total_count*100:.1f}%)")

    print("\n✅ Fallback mechanism testing completed!")
    return True

if __name__ == "__main__":
    test_fallback()