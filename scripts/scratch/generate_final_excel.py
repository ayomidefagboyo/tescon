import openpyxl
import pandas as pd

# 1. Read Excel and separate visible vs hidden rows
file_path = '/Users/admin/tescon/reports/Pending_Uncaptured_Full_Export_20260618_location_filtered.xlsx'
wb = openpyxl.load_workbook(file_path, data_only=True)
ws = wb['Pending Uncaptured']

headers = None
visible_data = []
hidden_data = []

# Assuming row 1 is headers based on my script output (since skiprows=1 in previous run skipped row 1 title, but wait!
# Previously my script output:
# R1: ('Whs', 'Coy', 'Location', ...)
# R2(Headers?): ('292000TLDE', 3483, 'EG6074022', ...)
# Wait, if R1 is the headers, then R1 is visible. So idx 0 is headers.
for idx, row in enumerate(ws.iter_rows(values_only=True)):
    if idx == 0:
        headers = row
        continue
        
    if not ws.row_dimensions[idx+1].hidden:
        visible_data.append(row)
    else:
        hidden_data.append(row)

# 2. Convert to DataFrame
df_vis = pd.DataFrame(visible_data, columns=headers)
df_hid = pd.DataFrame(hidden_data, columns=headers)

# Sort both sets by Location ASCENDING (from eg1 to eg3)
if 'Location' in df_vis.columns:
    df_vis = df_vis.sort_values(by='Location', ascending=True)
    df_hid = df_hid.sort_values(by='Location', ascending=True)

# Combine
df_combined = pd.concat([df_vis, df_hid], ignore_index=True)

# Select only the requested columns
cols_to_keep = ['Symbol Number', 'Location', 'Desc1', 'Desc2', 'BOH']
actual_cols = [c for c in cols_to_keep if c in df_combined.columns]

df_clean = df_combined[actual_cols].copy()

# Add S/N column at the beginning
df_clean.insert(0, 'S/N', range(1, len(df_clean) + 1))

# 4. Generate Excel
excel_path = '/Users/admin/tescon/reports/Pending_Uncaptured_Clean_Combined.xlsx'
df_clean.to_excel(excel_path, index=False)

print(f"Excel created at {excel_path}")

