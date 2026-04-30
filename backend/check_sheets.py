import pandas as pd
excel_file = "backend/data/Total EGTL Photo Project.xlsx"
xl = pd.ExcelFile(excel_file, engine='openpyxl')
print(f"Sheet names in {excel_file}: {xl.sheet_names}")
