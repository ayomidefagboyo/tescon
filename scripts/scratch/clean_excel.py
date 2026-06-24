#!/usr/bin/env python3
"""Clean up the Excel file by removing unnecessary columns and optimizing it."""

import pandas as pd
import sys

def clean_excel_file():
    print("🧹 Cleaning Excel file...")

    input_file = "egtl_cleaned_OPTIMIZED_20260124_131513.xlsx"
    output_file = "egtl_filtered_clean.xlsx"

    try:
        print(f"📂 Loading {input_file}...")

        # Define the columns we actually need
        required_columns = [
            'Whs', 'Location', 'Loc Type', 'Symbol Number',
            'Desc1', 'Desc2', 'Long Text Desc', 'UOM', 'BOH',
            'Min', 'Max', 'Item Pool', 'Unit Cost ($)', 'Unit Cost(N)',
            'Mfg Name', 'Part No', 'JDE long Text', 'DATA_FLAG'
        ]

        # Load only the required columns to avoid memory issues
        print("📋 Loading only essential columns...")
        df = pd.read_excel(input_file, sheet_name='DATA', usecols=required_columns)

        print(f"✅ Loaded {len(df)} rows with {len(df.columns)} columns")
        print(f"📊 Columns: {list(df.columns)}")

        # Keep all warehouses (no Whs filter)
        if 'Whs' in df.columns:
            print(f"🏢 Total warehouses: {df['Whs'].nunique()} (all selected)")
            print(f"📦 Warehouse distribution:")
            warehouse_counts = df['Whs'].value_counts().head(10)
            for whs, count in warehouse_counts.items():
                print(f"   {whs}: {count} parts")
            print("✅ Keeping all warehouses (no filter)")
            df_filtered = df.copy()
        else:
            print("⚠️  No Whs column found")
            df_filtered = df.copy()

        # BOH: exclude 0 and blanks (keep only rows with non-zero, non-blank BOH)
        if 'BOH' in df_filtered.columns:
            before_boh = len(df_filtered)
            boh_numeric = pd.to_numeric(df_filtered['BOH'], errors='coerce')
            # Keep only: BOH not null/blank and BOH > 0
            df_filtered = df_filtered[
                df_filtered['BOH'].notna()
                & (df_filtered['BOH'].astype(str).str.strip() != '')
                & (boh_numeric > 0)
            ].copy()
            print(f"📊 BOH filter: excluded 0 and blanks → {len(df_filtered)} rows (removed {before_boh - len(df_filtered)})")
        else:
            print("⚠️  No BOH column found, skipping BOH filter")

        # Remove rows with null symbol numbers
        initial_count = len(df_filtered)
        df_filtered = df_filtered.dropna(subset=['Symbol Number'])
        print(f"🚿 Removed {initial_count - len(df_filtered)} rows with null symbol numbers")

        # No deduplication: keep all rows (same symbol can appear in multiple Whs/Location with BOH > 0)
        print(f"📋 Keeping all {len(df_filtered)} rows (no deduplication by Symbol Number)")

        # Clean up the data
        print("🧽 Cleaning up data...")

        # Convert symbol numbers to strings
        df_filtered['Symbol Number'] = df_filtered['Symbol Number'].astype(str)

        # Fill null descriptions with empty strings
        for col in ['Desc1', 'Desc2', 'Long Text Desc']:
            if col in df_filtered.columns:
                df_filtered[col] = df_filtered[col].fillna('')

        # Fill null JDE long text
        if 'JDE long Text' in df_filtered.columns:
            df_filtered['JDE long Text'] = df_filtered['JDE long Text'].fillna('')

        print(f"📝 Final dataset: {len(df_filtered)} rows")

        # Visibility check: confirm Whs, BOH, Location are present
        visibility_cols = ['Whs', 'BOH', 'Location']
        present = [c for c in visibility_cols if c in df_filtered.columns]
        missing = [c for c in visibility_cols if c not in df_filtered.columns]
        print("\n👁 Visibility check:")
        print(f"   Present: {present}")
        if missing:
            print(f"   Missing: {missing}")

        # Show some sample data (include Location, Whs, BOH)
        sample_cols = ['Symbol Number', 'Desc1', 'Location', 'Whs', 'BOH', 'Mfg Name', 'Part No']
        sample_cols = [c for c in sample_cols if c in df_filtered.columns]
        print("\n📋 Sample data (with Location, Whs, BOH):")
        if len(df_filtered) > 0 and sample_cols:
            sample = df_filtered[sample_cols].head(3)
            for idx, row in sample.iterrows():
                parts = " | ".join(f"{c}={row.get(c, 'N/A')}" for c in sample_cols)
                print(f"  {parts}")

        # Save the cleaned file
        print(f"\n💾 Saving cleaned file as {output_file}...")
        df_filtered.to_excel(output_file, sheet_name='DATA', index=False, engine='openpyxl')

        # Check file sizes
        import os
        original_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
        new_size = os.path.getsize(output_file) / (1024 * 1024)  # MB

        print(f"✅ File saved successfully!")
        print(f"📊 Original file: {original_size:.1f} MB")
        print(f"📊 New file: {new_size:.1f} MB")
        print(f"🎯 Space saved: {original_size - new_size:.1f} MB ({((original_size - new_size) / original_size * 100):.1f}%)")

        print(f"\n🔄 To use this file, update worker.py to use: {output_file}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = clean_excel_file()
    if success:
        print("\n✅ Excel file cleaned successfully!")
    else:
        print("\n❌ Failed to clean Excel file")
        sys.exit(1)