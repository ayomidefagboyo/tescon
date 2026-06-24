import openpyxl
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A2
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import pandas as pd

# 1. Read Excel and extract visible rows
file_path = '/Users/admin/tescon/reports/Pending_Uncaptured_Full_Export_20260618_location_filtered.xlsx'
wb = openpyxl.load_workbook(file_path, data_only=True)
ws = wb['Pending Uncaptured']

visible_data = []
for idx, row in enumerate(ws.iter_rows(values_only=True)):
    if not ws.row_dimensions[idx+1].hidden:
        visible_data.append(row)

# The first row is the title? Wait, my script showed:
# R1: ('Whs', 'Coy', 'Location', ...)
# So R1 is the headers!
headers = visible_data[0]
data = visible_data[1:]

df = pd.DataFrame(data, columns=headers)

# Sort by Location descending
df = df.sort_values(by='Location', ascending=False)

# 2. Build PDF
# We will use A2 Landscape to fit 42 columns
pdf_path = '/Users/admin/tescon/reports/Pending_Uncaptured_Sorted.pdf'
doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A2), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)

# Replace None with empty string and truncate long strings to fit
def clean_val(val):
    if pd.isna(val) or val is None:
        return ""
    s = str(val)
    if len(s) > 15:
        return s[:13] + ".."
    return s

# Create table data
table_data = [ [clean_val(h) for h in headers] ]
for row in df.itertuples(index=False):
    table_data.append([clean_val(cell) for cell in row])

# Create table
table = Table(table_data)

# Add style
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
table.setStyle(style)

elements = [table]
doc.build(elements)
print(f"PDF created at {pdf_path}")

# Also create a sorted Excel file just in case!
excel_path = '/Users/admin/tescon/reports/Pending_Uncaptured_Sorted.xlsx'
df.to_excel(excel_path, index=False)
print(f"Excel created at {excel_path}")

