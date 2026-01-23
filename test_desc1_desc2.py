#!/usr/bin/env python3
"""Test that system now uses Desc1 + Desc2 for all descriptions."""

import sys
import os
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

from services.excel_service import get_excel_parts_service

def test_desc1_desc2():
    excel_service = get_excel_parts_service()
    excel_service.load_excel_file("backend/EGTL Dump_with_JDE.xlsx", sheet_name="Data")

    # Test multiple parts to verify all use Desc1 + Desc2
    test_symbols = ["19200790", "58018612", "58012661"]

    print("Testing that all parts now use Desc1 + Desc2 for long description")
    print("=" * 70)

    for symbol in test_symbols:
        print(f"\n📋 Testing Symbol: {symbol}")
        part_info = excel_service.get_part_info(symbol)

        if part_info:
            # Get raw data
            df = excel_service.unique_parts
            raw_match = df[df['Symbol Number'].astype(str) == symbol]
            if not raw_match.empty:
                row = raw_match.iloc[0]

                desc1 = str(row['Desc1']) if pd.notna(row['Desc1']) else ''
                desc2 = str(row['Desc2']) if pd.notna(row['Desc2']) else ''
                expected_desc = ' | '.join(filter(None, [desc1.strip(), desc2.strip()]))

                actual_desc = part_info.get('long_description', '')

                print(f"  Desc1: '{desc1}'")
                print(f"  Desc2: '{desc2}'")
                print(f"  Long Text JDE: '{row['Long Text JDE']}'")
                print(f"  Expected (Desc1 + Desc2): '{expected_desc}'")
                print(f"  Actual long_description: '{actual_desc}'")

                if actual_desc == expected_desc:
                    print(f"  ✅ CORRECT: Using Desc1 + Desc2")
                else:
                    print(f"  ❌ WRONG: Not using Desc1 + Desc2")

                # Show image layout preview
                print(f"\n  🖼️  IMAGE LAYOUT:")
                print(f"    1. SYMBOL NUMBER: {part_info.get('symbol_number')}")
                print(f"    2. LONG DESCRIPTION: {actual_desc[:60]}{'...' if len(actual_desc) > 60 else ''}")

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

    print("\n✅ Testing completed!")

if __name__ == "__main__":
    test_desc1_desc2()