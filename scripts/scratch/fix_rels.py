import zipfile
import shutil
import os

new = "EGTL_Photo_Project_Weekly Report (Jun 15, 2026) Rev 4.xlsx"
fixed = "EGTL_Photo_Project_Weekly Report (Jun 15, 2026) Rev 6.xlsx"

os.makedirs("tmp_fix", exist_ok=True)
with zipfile.ZipFile(new, 'r') as z:
    z.extractall("tmp_fix")

# Fix sheet1.xml.rels
rel_file = "tmp_fix/xl/worksheets/_rels/sheet1.xml.rels"
if os.path.exists(rel_file):
    with open(rel_file, 'r') as f:
        content = f.read()
    content = content.replace('Target="/xl/drawings/drawing1.xml"', 'Target="../drawings/drawing1.xml"')
    with open(rel_file, 'w') as f:
        f.write(content)

# Fix chart1.xml if openpyxl messed it up? 
# Wait, openpyxl removed style1.xml and colors1.xml!
# So maybe the file is corrupt because it's missing style/color XMLs!

# Let's restore the original chart XMLs from the original template into the new file!
orig = "EGTL_Photo_Project_Weekly Report (June 9th, 2026).xlsx"
with zipfile.ZipFile(orig, 'r') as z:
    z.extract("xl/charts/chart1.xml", "tmp_fix")
    if "xl/charts/style1.xml" in z.namelist():
        z.extract("xl/charts/style1.xml", "tmp_fix")
    if "xl/charts/colors1.xml" in z.namelist():
        z.extract("xl/charts/colors1.xml", "tmp_fix")
    z.extract("xl/drawings/drawing1.xml", "tmp_fix")

# Wait, the Content_Types.xml needs to be restored to have the style/colors entries!
with zipfile.ZipFile(orig, 'r') as z:
    z.extract("[Content_Types].xml", "tmp_fix")

shutil.make_archive("fixed6", "zip", "tmp_fix")
shutil.move("fixed6.zip", fixed)
print("Created Rev 6")
