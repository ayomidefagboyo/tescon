# TESCON Image Processing Tool - User Guide

## For Warehouse & Operations Teams

This guide explains how to use the TESCON image processing tool to prepare spare-part images for SharePoint upload.

---

## 🎯 Two Workflow Modes

The tool offers two ways to process images:

### 1. **Simple Workflow** (Recommended)
- Upload images (1-10 at a time)
- Enter part number
- System automatically:
  - Looks up part description, location, and notes from Google Sheets
  - Adds text labels to processed images
  - Saves to Google Drive in organized folders
  - Checks for duplicates
- **No manual filename formatting required!**

### 2. **Manual Workflow** (Advanced)
- Upload images with pre-formatted filenames
- System validates and processes
- Download ZIP file for SharePoint upload
- **Requires proper filename format** (see below)

**Switch between modes** using the toggle at the top of the page.

---

## 📸 Simple Workflow Guide

### Step 1: Select "Simple" Mode
- Click the **"Simple"** button at the top of the page

### Step 2: Enter Part Number
- Type the part number in the search box
- Select from autocomplete suggestions (if available)
- System will show part information:
  - Description
  - Location
  - Item Note (if available)

### Step 3: Upload Images
- Drag & drop 1-10 images
- Or click to browse and select
- View numbers are auto-assigned (1, 2, 3...)
- You can manually adjust view numbers if needed

### Step 4: Process
- Click **"Process Images"**
- System will:
  - Check for duplicates in Google Drive
  - Process images with background removal
  - Add text labels with part description
  - Save to Google Drive in part number folders

### Step 5: Access Results
- Images are automatically saved to Google Drive
- Organized in folders by part number
- Filenames: `PartNumber_ViewNumber_Description.jpg`
- Access via Google Drive link provided

**Note**: If duplicates are detected, you'll see a warning. Use different view numbers or delete existing images first.

---

## 📸 Manual Workflow: Before You Start - Image Naming

**CRITICAL**: All images must be named correctly before upload.

### Required Format

```
PartNumber_ViewNumber_Description.jpg
```

### Examples

✅ **Correct:**
```
58802935_1_BEARING.jpg
58802935_2_BEARING.jpg
74452282_1_FAN TYPE.jpg
12345678_3_PUMP ASSEMBLY.jpg
```

❌ **Incorrect:**
```
photo1.jpg              (missing all components)
58802935_BEARING.jpg    (missing view number)
58802935-1-BEARING.jpg  (using dashes instead of underscores)
```

### What Each Part Means

- **PartNumber**: The item/part number (e.g., `58802935`)
- **ViewNumber**: The angle/view (1, 2, 3, 4...)
  - View 1: Front
  - View 2: Side
  - View 3: Back
  - View 4: Top/Detail
- **Description**: Part type/description (e.g., `BEARING`, `FAN TYPE`, `PUMP ASSEMBLY`)
  - Can include spaces
  - Describe what the part is

---

## 🚀 Manual Workflow: Processing Steps

### Step 1: Upload Images

1. Open the tool: `http://localhost:4173`
2. Drag & drop your images OR click to browse
3. You can upload:
   - Individual image files
   - Multiple images at once
   - A ZIP file containing images

### Step 2: Review Upload Summary

The system automatically shows:
- ✅ **Valid files**: Correctly named images
- ❌ **Invalid files**: Files that don't match the naming format
- 📦 **Unique parts**: How many different parts you're uploading
- 📊 **Part breakdown**: List of part numbers found

### Step 3: Fix Invalid Names (if any)

If you see files with invalid names:

1. Click **"Rename"** on the invalid file
2. Fill in the three fields:
   - **Part Number** (e.g., `58802935`)
   - **View Number** (e.g., `1`, `2`, `3`)
   - **Location** (e.g., `EG1060007`)
3. Click **"Save"** - the file will be renamed
4. OR click **"Skip"** to exclude that file

### Step 4: Configure Processing Options

**Output Format:**
- **PNG**: Larger files, best quality, supports transparency
- **JPEG**: Smaller files, good quality (recommended for SharePoint)

**White Background:**
- Keep this **ON** for catalog images

**Compression:**
Choose a preset:
- **High Quality**: Largest files, highest quality
- **Balanced**: Recommended for most uses (default)
- **Web Optimized**: Good balance of size and quality
- **Compact**: Smallest files

### Step 5: Process Images

1. Click **"Process X files"** button
2. Wait for processing to complete
3. Monitor progress bar (shows X / Total images)

**For 1 image**: Processes instantly  
**For multiple images**: Processes in batches (you can close browser - job continues)

### Step 6: Download Results

When complete, you'll see:
- **"Download ZIP"** button
- Stats showing processed/failed counts

The ZIP file contains:
```
processed_[job_id].zip
├── 58802935/
│   ├── 58802935_1_EG1060007.jpg
│   ├── 58802935_2_EG1060007.jpg
│   └── 58802935_3_EG1060007.jpg
├── 74452282/
│   └── 74452282_1_EG1060007.jpg
```

**Each part has its own folder** - ready to upload directly to SharePoint!

### Step 7: Upload to SharePoint

1. Extract the ZIP file
2. You'll see folders named by part number
3. Upload each folder (or all at once) to SharePoint
4. Done! No manual sorting needed.

---

## ❗ Handling Failures

If some images fail:

1. Check the **Failed images** section
2. Review error messages
3. Click **"Retry X Failed"** to reprocess only failed images
4. OR download successful results and manually fix failed ones

Common failures:
- Image file corrupted
- Network timeout (will auto-retry)
- PicWish API rate limit (will auto-retry)

---

## 💡 Tips for Success

### Before Photography
- ✅ Agree on naming format with your team
- ✅ Name images immediately after capture
- ✅ Use consistent warehouse codes

### During Upload
- ✅ Check validation summary before processing
- ✅ Fix all invalid names first
- ✅ Use "Balanced" compression preset
- ✅ Keep white background ON

### After Processing
- ✅ Validate export shows no missing views
- ✅ Download and verify ZIP structure
- ✅ Upload directly to SharePoint

---

## 🆘 Troubleshooting

### "X files with invalid names"
**Solution**: Click "Rename" and fix each one, or "Skip" to exclude.

### "Processing failed"
**Solution**: Check your internet connection and click "Retry Failed".

### "Missing views detected"
**Solution**: Some parts are missing view angles (e.g., only view 1, but missing view 2). Upload missing views.

### Can't find processed images
**Solution**: Check the downloads folder - look for `processed_[job_id].zip`

---

## 📞 Support

For issues or questions, contact: **projects@teamsengineering.net**

---

## 🎯 Success Checklist

Before uploading to SharePoint, verify:

- [ ] All images have valid filenames
- [ ] Processing completed without failures
- [ ] Validation shows no missing views
- [ ] ZIP structure shows folders by part number
- [ ] Image quality is acceptable for catalog
- [ ] File sizes are reasonable (< 2MB per image)

---

**Prepared by TESCON Engineering Solutions & Consulting Services Ltd.**

