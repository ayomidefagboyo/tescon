#!/usr/bin/env python3
"""Simple test for fallback mechanism."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

from services.excel_service import get_excel_parts_service

def test_simple():
    excel_service = get_excel_parts_service()
    excel_service.load_excel_file("backend/EGTL Dump_with_JDE.xlsx", sheet_name="Data")

    # Test a part with missing Long Text JDE (58012661 from previous test)
    print("Testing part with missing Long Text JDE:")
    part_info = excel_service.get_part_info("58012661")
    if part_info:
        print(f"Symbol: {part_info.get('symbol_number')}")
        print(f"Long Description: '{part_info.get('long_description')}'")
        print(f"Desc1: '{part_info.get('description_1')}'")
        print(f"Desc2: '{part_info.get('description_2')}'")

        # Check if fallback is working
        long_desc = part_info.get('long_description', '')
        if ' | ' in long_desc:
            print("✅ FALLBACK WORKING: Using Desc1 + Desc2 with ' | ' separator")
        else:
            print("❌ FALLBACK NOT WORKING")

    print("\nTesting part with Long Text JDE:")
    part_info2 = excel_service.get_part_info("58018612")
    if part_info2:
        print(f"Symbol: {part_info2.get('symbol_number')}")
        print(f"Long Description: '{part_info2.get('long_description')}'")

        # Check if it's using JDE text (should not contain ' | ')
        long_desc = part_info2.get('long_description', '')
        if ' | ' not in long_desc and long_desc:
            print("✅ JDE TEXT WORKING: Using Long Text JDE directly")
        else:
            print("❌ JDE TEXT NOT WORKING")

if __name__ == "__main__":
    test_simple()