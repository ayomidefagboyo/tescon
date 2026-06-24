import pandas as pd
excel_file = "backend/data/Total EGTL Photo Project.xlsx"
df = pd.read_excel(excel_file, sheet_name='Photo Data', nrows=5, engine='openpyxl')
print(f"Columns: {list(df.columns)}")
