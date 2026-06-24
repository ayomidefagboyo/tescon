#!/usr/bin/env python3
import pandas as pd
import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent

INPUT_EXCEL = PROJECT_ROOT / "reports" / "Remaining_To_Shoot_By_Location.xlsx"
OUTPUT_EXCEL = PROJECT_ROOT / "reports" / "Physical_Shoot_List_Grouped.xlsx"

SIZE_PATTERN = re.compile(
    r'\b\d[\d./]*\s*(?:MM|CM|IN|FT|LB|KG|NB|BAR|PSI|KPA|DN|PN|SCH|STD|XS|XXS|CLASS|CL|OD|ID|WT|RF|FF|RTJ|SW|BW|THD|MNPT|FNPT|NPT|BSPT|BSP|#)\b'
    r'|["\']',
    re.IGNORECASE,
)

def base_desc(text) -> str:
    if pd.isna(text) or not text:
        return ""
    s = SIZE_PATTERN.sub("", str(text))
    s = re.sub(r'\b\d+(?:\.\d+)?(?:/\d+)?\b', "", s)
    return re.sub(r'\s+', " ", s).strip().upper()

def main():
    print(f"Reading {INPUT_EXCEL.name}...")
    df = pd.read_excel(INPUT_EXCEL)
    
    print("Grouping by base description...")
    df["Base Desc"] = df["Desc1"].apply(base_desc)
    
    # We want to keep track of the groups
    grouped = df.groupby("Base Desc")
    
    results = []
    
    # Sort groups by size (descending) so the biggest time-savers are at the top
    group_sizes = grouped.size().sort_values(ascending=False)
    
    total_to_shoot = 0
    total_proxies = 0
    
    for base, size in group_sizes.items():
        group_df = grouped.get_group(base).copy()
        
        # Sort within the group just to have a consistent "Lead"
        group_df = group_df.sort_values(by="Symbol Number")
        
        # The first item is the lead
        lead_symbol = group_df.iloc[0]["Symbol Number"]
        
        for i, (_, row) in enumerate(group_df.iterrows()):
            out_row = row.to_dict()
            if i == 0:
                out_row["Action Required"] = "📸 SHOOT THIS"
                out_row["Proxy Lead Symbol"] = "—"
                total_to_shoot += 1
            else:
                out_row["Action Required"] = "⏭️ SKIP (Proxy)"
                out_row["Proxy Lead Symbol"] = f"Use {lead_symbol}"
                total_proxies += 1
            results.append(out_row)
            
    # Convert back to dataframe
    out_df = pd.DataFrame(results)
    
    # Reorder columns to make it user friendly
    cols = ["Action Required", "Proxy Lead Symbol", "Symbol Number", "Location", "Desc1", "Base Desc", "Desc2", "BOH"]
    # Drop any cols that don't exist
    cols = [c for c in cols if c in out_df.columns]
    out_df = out_df[cols]
    
    print(f"\nGrouping Complete!")
    print(f"Total symbols   : {len(df)}")
    print(f"Unique to shoot : {total_to_shoot}")
    print(f"Skipped (proxy) : {total_proxies}")
    print(f"Time saved      : {(total_proxies/len(df))*100:.1f}% fewer photos!")
    
    out_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\nSaved grouped list to: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
