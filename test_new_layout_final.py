#!/usr/bin/env python3
"""Test the final layout format."""

import sys
import os
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

from services.excel_service import get_excel_parts_service

def test_final_layout():
    excel_service = get_excel_parts_service()
    excel_service.load_excel_file("backend/EGTL Dump_with_JDE.xlsx", sheet_name="Data")

    # Test multiple parts
    test_symbols = ["19200790", "58018612", "58012661"]

    print("Testing final layout format:")
    print("1. Symbol Number + Part Number (same line)")
    print("2. Manufacturer")
    print("3. Description 1")
    print("4. Description 2")
    print("=" * 70)

    for symbol in test_symbols:
        print(f"\n📋 Testing Symbol: {symbol}")
        part_info = excel_service.get_part_info(symbol)

        if part_info:
            # Show what the image layout would display
            print(f"  🖼️  IMAGE LAYOUT PREVIEW:")

            # Line 1: Symbol Number + Part Number
            sym = part_info.get('symbol_number')
            part_num = part_info.get('part_number')
            if sym and part_num:
                print(f"    1. SYMBOL NUMBER: {sym}    PART NUMBER: {part_num}")
            elif sym:
                print(f"    1. SYMBOL NUMBER: {sym}")
            elif part_num:
                print(f"    1. PART NUMBER: {part_num}")

            # Line 2: Manufacturer
            manuf = part_info.get('manufacturer')
            if manuf:
                print(f"    2. MANUFACTURER: {manuf}")

            # Line 3: Description 1
            desc1 = part_info.get('description_1')
            if desc1:
                print(f"    3. DESCRIPTION 1: {desc1}")

            # Line 4: Description 2
            desc2 = part_info.get('description_2')
            if desc2:
                print(f"    4. DESCRIPTION 2: {desc2}")

        else:
            print(f"  ❌ Part not found")

    print("\n✅ Layout testing completed!")

if __name__ == "__main__":
    test_final_layout()