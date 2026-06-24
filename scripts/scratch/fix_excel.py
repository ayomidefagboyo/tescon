import zipfile
import shutil
import os

orig = "EGTL_Photo_Project_Weekly Report (June 9th, 2026).xlsx"
new = "EGTL_Photo_Project_Weekly Report (Jun 15, 2026) Rev 4.xlsx"
fixed = "EGTL_Photo_Project_Weekly Report (Jun 15, 2026) Rev 5.xlsx"

os.makedirs("tmp_orig", exist_ok=True)
os.makedirs("tmp_new", exist_ok=True)

with zipfile.ZipFile(orig, 'r') as z:
    z.extractall("tmp_orig")

with zipfile.ZipFile(new, 'r') as z:
    z.extractall("tmp_new")

# Copy worksheets
shutil.copytree("tmp_new/xl/worksheets", "tmp_orig/xl/worksheets", dirs_exist_ok=True)

# Copy sharedStrings
if os.path.exists("tmp_new/xl/sharedStrings.xml"):
    shutil.copy("tmp_new/xl/sharedStrings.xml", "tmp_orig/xl/sharedStrings.xml")

# Remove calcChain to force recalculation
if os.path.exists("tmp_orig/xl/calcChain.xml"):
    os.remove("tmp_orig/xl/calcChain.xml")

# Repackage
shutil.make_archive("fixed", "zip", "tmp_orig")
shutil.move("fixed.zip", fixed)

print("Created Rev 5")
