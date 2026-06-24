#!/usr/bin/env python3
"""Count unique symbol numbers after applying filters."""

import pandas as pd

def count_filtered_items():
    input_file = "egtl_cleaned_OPTIMIZED_20260124_131513.xlsx"
    
    print("📊 Analyzing Excel file...")
    
    # Required columns
    required_columns = [
        'Whs', 'Location', 'Loc Type', 'Symbol Number',
        'Desc1', 'Desc2', 'Long Text Desc', 'UOM', 'BOH',
        'Min', 'Max', 'Item Pool', 'Unit Cost ($)', 'Unit Cost(N)',
        'Mfg Name', 'Part No', 'JDE long Text', 'DATA_FLAG'
    ]
    
    # Load data
    df = pd.read_excel(input_file, sheet_name='DATA', usecols=required_columns)
    print(f"✅ Loaded {len(df)} total rows")
    
    # Initial unique symbol numbers
    initial_unique = df['Symbol Number'].nunique()
    print(f"📋 Initial unique symbol numbers: {initial_unique}")
    
    # Keep all warehouses (no filter)
    print(f"\n🏢 Total warehouses: {df['Whs'].nunique()} (all selected)")
    
    # BOH filter: exclude 0 and blanks
    if 'BOH' in df.columns:
        before_boh = len(df)
        boh_numeric = pd.to_numeric(df['BOH'], errors='coerce')
        df_filtered = df[
            df['BOH'].notna()
            & (df['BOH'].astype(str).str.strip() != '')
            & (boh_numeric > 0)
        ].copy()
        print(f"📊 After BOH filter (>0, non-blank): {len(df_filtered)} rows (removed {before_boh - len(df_filtered)})")
    else:
        df_filtered = df.copy()
    
    # Remove null symbol numbers
    before_null = len(df_filtered)
    df_filtered = df_filtered.dropna(subset=['Symbol Number'])
    print(f"🚿 After removing null symbol numbers: {len(df_filtered)} rows (removed {before_null - len(df_filtered)})")
    
    # Remove duplicates (keep first occurrence)
    before_dedup = len(df_filtered)
    df_filtered = df_filtered.drop_duplicates(subset=['Symbol Number'], keep='first')
    print(f"🔄 After deduplication: {len(df_filtered)} rows (removed {before_dedup - len(df_filtered)} duplicates)")
    
    # Final count
    final_unique = df_filtered['Symbol Number'].nunique()
    print(f"\n✅ FINAL RESULT:")
    print(f"   📦 Unique Symbol Numbers: {final_unique}")
    print(f"   📊 Total rows: {len(df_filtered)}")
    print(f"   📉 Reduction: {initial_unique - final_unique} symbol numbers removed")
    
    return final_unique

if __name__ == "__main__":
    count_filtered_items()
