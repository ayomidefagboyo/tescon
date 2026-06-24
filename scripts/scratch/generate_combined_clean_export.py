import openpyxl
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

# 1. Read Excel and separate visible vs hidden rows
file_path = '/Users/admin/tescon/reports/Pending_Uncaptured_Full_Export_20260618_location_filtered.xlsx'
wb = openpyxl.load_workbook(file_path, data_only=True)
ws = wb['Pending Uncaptured']

headers = None
visible_data = []
hidden_data = []

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

# Sort both sets by Location descending
if 'Location' in df_vis.columns:
    df_vis = df_vis.sort_values(by='Location', ascending=False)
    df_hid = df_hid.sort_values(by='Location', ascending=False)

# Combine
df_combined = pd.concat([df_vis, df_hid], ignore_index=True)

# Select only the requested columns
cols_to_keep = ['Symbol Number', 'Location', 'Item Desc 1', 'Item Desc 2', 'BOH']
# Handle missing columns gracefully
actual_cols = [c for c in cols_to_keep if c in df_combined.columns]

df_clean = df_combined[actual_cols].copy()

# Add S/N column
df_clean.insert(0, 'S/N', range(1, len(df_clean) + 1))

# Rename columns to match user request better
rename_map = {
    'Item Desc 1': 'Desc 1',
    'Item Desc 2': 'Desc 2',
}
df_clean.rename(columns=rename_map, inplace=True)
final_headers = df_clean.columns.tolist()

# 4. Generate Excel
excel_path = '/Users/admin/tescon/reports/Pending_Uncaptured_Clean_Combined.xlsx'
df_clean.to_excel(excel_path, index=False)
print(f"Excel created at {excel_path}")

# 5. Generate PDF
pdf_path = '/Users/admin/tescon/reports/Pending_Uncaptured_Clean_Combined.pdf'
doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)

def clean_val(val, col_name):
    if pd.isna(val) or val is None:
        return ""
    s = str(val)
    # Truncate descriptions slightly if they are super long
    if 'Desc' in col_name and len(s) > 40:
        return s[:37] + "..."
    return s

table_data = [ final_headers ]
for row in df_clean.itertuples(index=False):
    table_data.append([clean_val(cell, col) for cell, col in zip(row, final_headers)])

# Compute column widths roughly (A4 landscape is ~842 points wide, minus 40 margins = ~800 points)
# S/N (40), Symbol (70), Location (80), Desc1 (280), Desc2 (280), BOH (50)
col_widths = [40, 70, 80, 280, 280, 50]

table = Table(table_data, colWidths=col_widths, repeatRows=1)

style = TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('TOPPADDING', (0, 0), (-1, 0), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
])

# Divider line
vis_count = len(df_vis)
if vis_count > 0 and vis_count < len(df_combined):
    style.add('LINEBELOW', (0, vis_count), (-1, vis_count), 2, colors.red)

table.setStyle(style)
elements = [table]
doc.build(elements)
print(f"PDF created at {pdf_path}")
