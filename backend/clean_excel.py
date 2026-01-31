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
        df = pd.read_excel(input_file, sheet_name='Sheet1', usecols=required_columns)

        print(f"✅ Loaded {len(df)} rows with {len(df.columns)} columns")
        print(f"📊 Columns: {list(df.columns)}")

        # Check for warehouse filtering
        if 'Whs' in df.columns:
            print(f"🏢 Total warehouses: {df['Whs'].nunique()}")
            print(f"📦 Warehouse distribution:")
            warehouse_counts = df['Whs'].value_counts().head(10)
            for whs, count in warehouse_counts.items():
                print(f"   {whs}: {count} parts")

            # Filter for the specific warehouse if it exists
            if '29300000TL' in df['Whs'].values:
                print(f"\n🎯 Filtering for warehouse 29300000TL...")
                df_filtered = df[df['Whs'] == '29300000TL'].copy()
                print(f"✅ Filtered to {len(df_filtered)} parts for warehouse 29300000TL")
            else:
                print("⚠️  Warehouse 29300000TL not found, keeping all data")
                df_filtered = df.copy()
        else:
            print("⚠️  No Whs column found, keeping all data")
            df_filtered = df.copy()

        # Remove rows with null symbol numbers
        initial_count = len(df_filtered)
        df_filtered = df_filtered.dropna(subset=['Symbol Number'])
        print(f"🚿 Removed {initial_count - len(df_filtered)} rows with null symbol numbers")

        # Remove duplicate symbol numbers
        initial_count = len(df_filtered)
        df_filtered = df_filtered.drop_duplicates(subset=['Symbol Number'], keep='first')
        print(f"🔄 Removed {initial_count - len(df_filtered)} duplicate symbol numbers")

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

        print(f"📝 Final dataset: {len(df_filtered)} unique parts")

        # Show some sample data
        print("\n📋 Sample data:")
        if len(df_filtered) > 0:
            sample = df_filtered[['Symbol Number', 'Desc1', 'Desc2', 'Mfg Name', 'Part No']].head(3)
            for idx, row in sample.iterrows():
                print(f"  {row['Symbol Number']}: {row['Desc1']} | {row.get('Mfg Name', 'N/A')} | {row.get('Part No', 'N/A')}")

        # Save the cleaned file
        print(f"\n💾 Saving cleaned file as {output_file}...")
        df_filtered.to_excel(output_file, sheet_name='Sheet1', index=False, engine='openpyxl')

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