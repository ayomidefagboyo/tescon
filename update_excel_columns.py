#!/usr/bin/env python3
"""
Script to add Part Number and Manufacturer columns to the Excel file.
"""

import pandas as pd
import sys
from pathlib import Path

def update_excel_with_new_columns(input_file: str, output_file: str = None):
    """
    Add Part Number and Manufacturer columns to the Excel file.

    Args:
        input_file: Path to existing Excel file
        output_file: Path to save updated Excel file (default: overwrites input)
    """
    try:
        # Load existing data
        print(f"Loading {input_file}...")
        df = pd.read_excel(input_file, sheet_name='Data')
        print(f"Loaded {len(df)} rows with {len(df.columns)} columns")

        # Add Part Number column (default to Symbol Number)
        if 'Part Number' not in df.columns:
            df['Part Number'] = df['Symbol Number'].astype(str)
            print("✅ Added 'Part Number' column (defaulted to Symbol Number)")
        else:
            print("⚠️  'Part Number' column already exists")

        # Add Manufacturer column (empty by default - to be filled manually)
        if 'Manufacturer' not in df.columns:
            df['Manufacturer'] = ''  # Empty string by default
            print("✅ Added 'Manufacturer' column (empty - to be filled)")
        else:
            print("⚠️  'Manufacturer' column already exists")

        # Optionally try to extract manufacturer from descriptions
        # This is a basic attempt - you might need to customize this logic
        def extract_manufacturer(desc1, desc2, long_desc):
            """Try to extract manufacturer from description fields."""
            all_text = f"{str(desc1)} {str(desc2)} {str(long_desc)}".upper()

            # Common manufacturer patterns (add more as needed)
            manufacturers = [
                'JOHNSON MATTHEY', 'SIEMENS', 'ABB', 'SCHNEIDER', 'HONEYWELL',
                'EMERSON', 'YOKOGAWA', 'FOXBORO', 'ROSEMOUNT', 'FISHER',
                'VALVE-TECH', 'PENTAIR', 'ITT', 'GOULDS', 'GRUNDFOS',
                'KSB', 'FLOWSERVE', 'SULZER', 'ANDRITZ', 'ALFA LAVAL'
            ]

            for mfg in manufacturers:
                if mfg in all_text:
                    return mfg.title()  # Return in Title Case

            return ''  # No manufacturer found

        # Auto-populate manufacturer where possible
        if df['Manufacturer'].isna().all() or (df['Manufacturer'] == '').all():
            print("🔍 Attempting to extract manufacturers from descriptions...")
            df['Manufacturer'] = df.apply(
                lambda row: extract_manufacturer(
                    row['Desc1'],
                    row['Desc2'],
                    row['Long Text Desc']
                ), axis=1
            )

            # Show results
            populated_count = len(df[df['Manufacturer'] != ''])
            print(f"📊 Auto-populated {populated_count}/{len(df)} manufacturer fields")

            if populated_count > 0:
                print("Sample extracted manufacturers:")
                sample_mfgs = df[df['Manufacturer'] != '']['Manufacturer'].value_counts().head(10)
                for mfg, count in sample_mfgs.items():
                    print(f"  {mfg}: {count} items")

        # Reorder columns to put new fields after core fields
        column_order = ['Whs', 'Location', 'Symbol Number', 'Part Number', 'Manufacturer',
                       'Desc1', 'Desc2', 'Long Text Desc'] + \
                      [col for col in df.columns if col not in
                       ['Whs', 'Location', 'Symbol Number', 'Part Number', 'Manufacturer',
                        'Desc1', 'Desc2', 'Long Text Desc']]

        df = df[column_order]

        # Save updated file
        output_path = output_file or input_file
        print(f"💾 Saving to {output_path}...")

        # Create backup first
        if output_path == input_file:
            backup_path = input_file.replace('.xlsx', '_backup.xlsx')
            print(f"📋 Creating backup: {backup_path}")
            import shutil
            shutil.copy2(input_file, backup_path)

        # Save with openpyxl (built-in with pandas)
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Data', index=False)

        print(f"✅ Successfully updated Excel file!")
        print(f"📈 Final shape: {df.shape}")
        print("New columns:")
        for i, col in enumerate(df.columns):
            if col in ['Part Number', 'Manufacturer']:
                print(f"  {i+1}. {col} ⭐")
            else:
                print(f"  {i+1}. {col}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    input_file = "./backend/EGTL Dump Total Dump ( sorted).xlsx"

    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    else:
        output_file = None  # Overwrite original

    success = update_excel_with_new_columns(input_file, output_file)
    sys.exit(0 if success else 1)