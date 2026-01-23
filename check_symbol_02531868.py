#!/usr/bin/env python3
"""Check if symbol number 02531868 exists in Excel sheet."""

import sys
import os
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

from services.excel_service import get_excel_parts_service

def check_symbol():
    print("Checking symbol number: 02531868")
    print("=" * 60)

    # Load Excel service
    excel_service = get_excel_parts_service()
    excel_service.load_excel_file("backend/EGTL Dump_with_JDE.xlsx", sheet_name="Data")

    symbol = "02531868"

    print(f"🔍 Searching for symbol: {symbol}")

    # Check through the service first
    part_info = excel_service.get_part_info(symbol)
    if part_info:
        print("✅ Found through Excel service:")
        print(f"  Symbol Number: {part_info.get('symbol_number')}")
        print(f"  Part Number: {part_info.get('part_number')}")
        print(f"  Manufacturer: {part_info.get('manufacturer')}")
        print(f"  Description 1: {part_info.get('description_1')}")
        print(f"  Description 2: {part_info.get('description_2')}")
        return True

    print("❌ Not found through Excel service")

    # Check raw Excel data directly
    df = excel_service.unique_parts
    if df is not None:
        print(f"\n🔍 Searching raw Excel data (Total rows: {len(df)})")

        # Try different search methods
        searches = [
            ("Exact string match", df['Symbol Number'].astype(str) == symbol),
            ("String contains", df['Symbol Number'].astype(str).str.contains(symbol, na=False)),
            ("Numeric match (if applicable)", df['Symbol Number'] == int(symbol) if symbol.isdigit() else pd.Series([False] * len(df))),
            ("Strip whitespace", df['Symbol Number'].astype(str).str.strip() == symbol.strip())
        ]

        found_any = False
        for search_name, mask in searches:
            matches = df[mask]
            if not matches.empty:
                found_any = True
                print(f"\n✅ Found with {search_name}:")
                for idx, row in matches.head(3).iterrows():  # Show max 3 matches
                    print(f"  Row {idx}: Symbol='{row['Symbol Number']}', Part No='{row['Part No']}', Mfg='{row['Mfg Name']}'")

        if not found_any:
            print("\n❌ Not found in raw Excel data either")

            # Show some nearby symbol numbers for reference
            print("\n📋 Sample symbol numbers from Excel (first 10 rows):")
            sample_symbols = df['Symbol Number'].head(10)
            for i, sym in enumerate(sample_symbols):
                print(f"  {i+1}: {sym}")

            # Check if it might be a formatting issue
            print(f"\n🔍 Looking for similar symbol numbers:")
            partial_matches = df[df['Symbol Number'].astype(str).str.contains('02531', na=False)]
            if not partial_matches.empty:
                print("Found partial matches:")
                for idx, row in partial_matches.head(5).iterrows():
                    print(f"  Symbol: {row['Symbol Number']}")
            else:
                print("No partial matches found")

            # Look for numbers that start with 025
            prefix_matches = df[df['Symbol Number'].astype(str).str.startswith('025', na=False)]
            if not prefix_matches.empty:
                print(f"\nFound {len(prefix_matches)} symbols starting with '025':")
                for idx, row in prefix_matches.head(5).iterrows():
                    print(f"  Symbol: {row['Symbol Number']}")
            else:
                print("No symbols starting with '025' found")

    return False

if __name__ == "__main__":
    check_symbol()