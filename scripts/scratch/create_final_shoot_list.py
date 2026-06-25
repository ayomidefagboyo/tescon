#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

GROUPED_EXCEL = PROJECT_ROOT / "reports" / "Physical_Shoot_List_Grouped.xlsx"
FINAL_EXCEL = PROJECT_ROOT / "reports" / "Final_Physical_Shoot_List.xlsx"

def main():
    print(f"Reading {GROUPED_EXCEL.name}...")
    df = pd.read_excel(GROUPED_EXCEL)
    
    # Filter to only the ones we need to shoot
    shoot_df = df[df["Action Required"] == "📸 SHOOT THIS"].copy()
    
    # Keep only the original columns
    cols_to_keep = ["Symbol Number", "Location", "Desc1", "Desc2", "BOH"]
    shoot_df = shoot_df[cols_to_keep]
    
    # Sort by Location then Symbol Number
    shoot_df.sort_values(by=["Location", "Symbol Number"], inplace=True)
    
    # Recalculate S/N after sorting
    shoot_df.insert(0, 'S/N', range(1, 1 + len(shoot_df)))
    
    shoot_df.to_excel(FINAL_EXCEL, index=False)
    print(f"Saved {len(shoot_df)} items to {FINAL_EXCEL.name}")

if __name__ == "__main__":
    main()
