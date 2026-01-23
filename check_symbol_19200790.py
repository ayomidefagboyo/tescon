#!/usr/bin/env python3
"""Check specific symbol number 19200790."""

import sys
import os
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

from services.excel_service import get_excel_parts_service

def check_symbol():
    excel_service = get_excel_parts_service()
    excel_service.load_excel_file("backend/EGTL Dump_with_JDE.xlsx", sheet_name="Data")

    symbol = "19200790"
    print(f"Checking Symbol Number: {symbol}")
    print("=" * 60)

    # Get part info through the service
    part_info = excel_service.get_part_info(symbol)

    if not part_info:
        print("❌ Part not found in the system")

        # Check if it exists in the raw data
        df = excel_service.unique_parts
        raw_match = df[df['Symbol Number'].astype(str) == symbol]

        if raw_match.empty:
            print("❌ Part not found in raw Excel data either")
            print(f"\nShowing first few symbol numbers for reference:")
            sample_symbols = df['Symbol Number'].head(10).astype(str)
            for s in sample_symbols:
                print(f"  {s}")
        else:
            print("✅ Part found in raw data but not returned by service")
            print("Raw data:")
            for col in ['Symbol Number', 'Part No', 'Mfg Name', 'Long Text JDE', 'Desc1', 'Desc2']:
                if col in raw_match.columns:
                    print(f"  {col}: {raw_match[col].iloc[0]}")
        return

    print("✅ Part found in system")
    print(f"Symbol Number: {part_info.get('symbol_number')}")
    print(f"Part Number: {part_info.get('part_number')}")
    print(f"Manufacturer: {part_info.get('manufacturer')}")
    print(f"Description 1: {part_info.get('description_1')}")
    print(f"Description 2: {part_info.get('description_2')}")
    print(f"Long Description: {part_info.get('long_description')}")
    print(f"Location: {part_info.get('location')}")

    # Get raw data to see what's in the Excel
    df = excel_service.unique_parts
    raw_match = df[df['Symbol Number'].astype(str) == symbol]

    if not raw_match.empty:
        row = raw_match.iloc[0]
        print(f"\n📄 RAW EXCEL DATA:")
        print(f"  Symbol Number: '{row['Symbol Number']}'")
        print(f"  Part No: '{row['Part No']}'")
        print(f"  Mfg Name: '{row['Mfg Name']}'")
        print(f"  Long Text JDE: '{row['Long Text JDE']}'")
        print(f"  Desc1: '{row['Desc1']}'")
        print(f"  Desc2: '{row['Desc2']}'")
        print(f"  Location: '{row['Location']}'")

        # Check fallback logic
        print(f"\n🔄 FALLBACK ANALYSIS:")
        jde_text = row['Long Text JDE']
        is_jde_empty = pd.isna(jde_text) or str(jde_text).strip() == '' or str(jde_text).lower() == 'nan'

        if is_jde_empty:
            print(f"  Long Text JDE is empty/nan - SHOULD use fallback")
            desc1 = str(row['Desc1']) if pd.notna(row['Desc1']) else ''
            desc2 = str(row['Desc2']) if pd.notna(row['Desc2']) else ''
            expected_fallback = ' | '.join(filter(None, [desc1.strip(), desc2.strip()]))
            print(f"  Expected fallback: '{expected_fallback}'")
        else:
            print(f"  Long Text JDE is available - should use JDE text")

        # Show what the image layout would display
        print(f"\n🖼️  IMAGE LAYOUT PREVIEW:")
        print(f"  1. SYMBOL NUMBER: {part_info.get('symbol_number')}")

        long_desc = part_info.get('long_description', '')
        if long_desc:
            preview = long_desc[:60] + ('...' if len(long_desc) > 60 else '')
            print(f"  2. LONG DESCRIPTION: {preview}")
        else:
            print(f"  2. LONG DESCRIPTION: [No description available]")

        part_num = part_info.get('part_number')
        manuf = part_info.get('manufacturer')
        if part_num and manuf:
            print(f"  3. PART NUMBER: {part_num}    MANUFACTURER: {manuf}")
        elif part_num:
            print(f"  3. PART NUMBER: {part_num}")
        elif manuf:
            print(f"  3. MANUFACTURER: {manuf}")

if __name__ == "__main__":
    check_symbol()