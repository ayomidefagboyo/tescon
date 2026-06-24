import openpyxl
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A2
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

# 2. Sort both sets
df_vis = pd.DataFrame(visible_data, columns=headers)
df_hid = pd.DataFrame(hidden_data, columns=headers)

df_vis = df_vis.sort_values(by='Location', ascending=False)
df_hid = df_hid.sort_values(by='Location', ascending=False)

# 3. Combine
df_combined = pd.concat([df_vis, df_hid], ignore_index=True)

# 4. Generate Excel
excel_path = '/Users/admin/tescon/reports/Pending_Uncaptured_Combined_Sorted.xlsx'
df_combined.to_excel(excel_path, index=False)
print(f"Excel created at {excel_path}")

# 5. Generate PDF
pdf_path = '/Users/admin/tescon/reports/Pending_Uncaptured_Combined_Sorted.pdf'
doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A2), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)

def clean_val(val):
    if pd.isna(val) or val is None:
        return ""
    s = str(val)
    if len(s) > 15:
        return s[:13] + ".."
    return s

table_data = [ [clean_val(h) for h in headers] ]
for row in df_combined.itertuples(index=False):
    table_data.append([clean_val(cell) for cell in row])

table = Table(table_data)

style = TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 8),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
    ('FONTSIZE', (0, 1), (-1, -1), 6),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
])

# Let's add a divider line between the two sections to make it clear
vis_count = len(df_vis)
if vis_count > 0:
    style.add('LINEBELOW', (0, vis_count), (-1, vis_count), 2, colors.red)

table.setStyle(style)
elements = [table]
doc.build(elements)
print(f"PDF created at {pdf_path}")

