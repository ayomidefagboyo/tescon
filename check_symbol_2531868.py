#!/usr/bin/env python3
"""Check the found symbol 2531868 details."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

from services.excel_service import get_excel_parts_service

def check_found_symbol():
    excel_service = get_excel_parts_service()
    excel_service.load_excel_file("backend/EGTL Dump_with_JDE.xlsx", sheet_name="Data")

    symbol = "2531868"
    print(f"Found symbol: {symbol} (without leading zero)")
    print("=" * 60)

    part_info = excel_service.get_part_info(symbol)
    if part_info:
        print("✅ Full part details:")
        print(f"  Symbol Number: {part_info.get('symbol_number')}")
        print(f"  Part Number: {part_info.get('part_number')}")
        print(f"  Manufacturer: {part_info.get('manufacturer')}")
        print(f"  Description 1: {part_info.get('description_1')}")
        print(f"  Description 2: {part_info.get('description_2')}")
        print(f"  Location: {part_info.get('location')}")

        # Show how it would appear on the image
        print(f"\n🖼️  IMAGE LAYOUT PREVIEW:")
        sym = part_info.get('symbol_number')
        part_num = part_info.get('part_number')
        manuf = part_info.get('manufacturer')
        desc1 = part_info.get('description_1')
        desc2 = part_info.get('description_2')

        if sym and part_num:
            print(f"  1. SYMBOL NUMBER: {sym}    PART NUMBER: {part_num}")
        elif sym:
            print(f"  1. SYMBOL NUMBER: {sym}")

        if manuf:
            print(f"  2. MANUFACTURER: {manuf}")
        if desc1:
            print(f"  3. DESCRIPTION 1: {desc1}")
        if desc2:
            print(f"  4. DESCRIPTION 2: {desc2}")

    else:
        print("❌ Still not found through service")

if __name__ == "__main__":
    check_found_symbol()