#!/usr/bin/env python3
"""Create a separate Excel file with items where BOH > 0 and Location contains 'GTA'."""

import pandas as pd
import sys

def create_gta_excel():
    print("🔍 Creating GTA-filtered Excel file...")

    input_file = "egtl_cleaned_OPTIMIZED_20260124_131513.xlsx"
    output_file = "egtl_GTA_BOH_filtered.xlsx"

    try:
        print(f"📂 Loading {input_file}...")

        # Define the columns we need
        required_columns = [
            'Whs', 'Location', 'Loc Type', 'Symbol Number',
            'Desc1', 'Desc2', 'Long Text Desc', 'UOM', 'BOH',
            'Min', 'Max', 'Item Pool', 'Unit Cost ($)', 'Unit Cost(N)',
            'Mfg Name', 'Part No', 'JDE long Text', 'DATA_FLAG'
        ]

        # Load only the required columns
        print("📋 Loading essential columns...")
        df = pd.read_excel(input_file, sheet_name='DATA', usecols=required_columns)

        print(f"✅ Loaded {len(df)} total rows")
        print(f"📊 Columns: {list(df.columns)}")

        # Initial count
        initial_count = len(df)
        print(f"\n📋 Initial rows: {initial_count}")

        # Filter 1: BOH > 0 and non-blank
        if 'BOH' in df.columns:
            boh_numeric = pd.to_numeric(df['BOH'], errors='coerce')
            df_filtered = df[
                df['BOH'].notna()
                & (df['BOH'].astype(str).str.strip() != '')
                & (boh_numeric > 0)
            ].copy()
            print(f"📊 After BOH filter (>0, non-blank): {len(df_filtered)} rows (removed {initial_count - len(df_filtered)})")
        else:
            print("⚠️  No BOH column found")
            df_filtered = df.copy()

        # Filter 2: Location contains 'GTA'
        if 'Location' in df_filtered.columns:
            before_location = len(df_filtered)
            # Case-insensitive search for 'GTA' in Location column
            df_filtered = df_filtered[
                df_filtered['Location'].notna()
                & (df_filtered['Location'].astype(str).str.upper().str.contains('GTA', na=False))
            ].copy()
            print(f"📍 After Location contains 'GTA' filter: {len(df_filtered)} rows (removed {before_location - len(df_filtered)})")
        else:
            print("⚠️  No Location column found")
            return False

        # Remove rows with null symbol numbers
        before_null = len(df_filtered)
        df_filtered = df_filtered.dropna(subset=['Symbol Number'])
        print(f"🚿 After removing null symbol numbers: {len(df_filtered)} rows (removed {before_null - len(df_filtered)})")

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

        # Final stats
        final_count = len(df_filtered)
        unique_symbols = df_filtered['Symbol Number'].nunique()
        
        print(f"\n📝 Final dataset: {final_count} rows")
        print(f"📦 Unique Symbol Numbers: {unique_symbols}")
        
        if 'Whs' in df_filtered.columns:
            print(f"🏢 Warehouses: {df_filtered['Whs'].nunique()}")
            print(f"📦 Warehouse distribution:")
            warehouse_counts = df_filtered['Whs'].value_counts()
            for whs, count in warehouse_counts.items():
                print(f"   {whs}: {count} parts")

        # Visibility check
        visibility_cols = ['Whs', 'BOH', 'Location']
        present = [c for c in visibility_cols if c in df_filtered.columns]
        missing = [c for c in visibility_cols if c not in df_filtered.columns]
        print("\n👁 Visibility check:")
        print(f"   Present: {present}")
        if missing:
            print(f"   Missing: {missing}")

        # Show sample data
        sample_cols = ['Symbol Number', 'Desc1', 'Location', 'Whs', 'BOH', 'Mfg Name', 'Part No']
        sample_cols = [c for c in sample_cols if c in df_filtered.columns]
        print("\n📋 Sample data (with Location, Whs, BOH):")
        if len(df_filtered) > 0 and sample_cols:
            sample = df_filtered[sample_cols].head(5)
            for idx, row in sample.iterrows():
                parts = " | ".join(f"{c}={row.get(c, 'N/A')}" for c in sample_cols)
                print(f"  {parts}")

        # Save the filtered file
        print(f"\n💾 Saving GTA-filtered file as {output_file}...")
        df_filtered.to_excel(output_file, sheet_name='DATA', index=False, engine='openpyxl')

        # Check file sizes
        import os
        original_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
        new_size = os.path.getsize(output_file) / (1024 * 1024)  # MB

        print(f"✅ File saved successfully!")
        print(f"📊 Original file: {original_size:.1f} MB")
        print(f"📊 New file: {new_size:.1f} MB")
        print(f"🎯 Filtered to: {final_count} rows with BOH > 0 and Location containing 'GTA'")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_gta_excel()
    if success:
        print("\n✅ GTA-filtered Excel file created successfully!")
    else:
        print("\n❌ Failed to create GTA-filtered Excel file")
        sys.exit(1)
