# Google Cloud Setup Guide

This guide walks you through setting up Google Cloud credentials for Google Sheets and Google Drive integration.

## Prerequisites

- Google account
- Access to the Google Sheet you want to use
- Access to Google Drive folder where images will be saved

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click **"New Project"**
4. Enter project name: `tescon-image-processor` (or your preferred name)
5. Click **"Create"**
6. Wait for project creation (takes a few seconds)
7. Select the new project from the dropdown

## Step 2: Enable Required APIs

1. In the Google Cloud Console, go to **"APIs & Services"** → **"Library"**
2. Search for **"Google Sheets API"** and click on it
3. Click **"Enable"**
4. Go back to Library
5. Search for **"Google Drive API"** and click on it
6. Click **"Enable"**

## Step 3: Create Service Account

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"Service account"**
3. Enter service account details:
   - **Service account name**: `tescon-service-account`
   - **Service account ID**: (auto-generated, you can change it)
   - **Description**: "Service account for TESCON image processing"
4. Click **"Create and Continue"**
5. Skip the optional step (Grant access) → Click **"Continue"**
6. Click **"Done"**

## Step 4: Create and Download Key

1. In the **"Credentials"** page, find your service account
2. Click on the service account email
3. Go to the **"Keys"** tab
4. Click **"Add Key"** → **"Create new key"**
5. Select **"JSON"** format
6. Click **"Create"**
7. The JSON file will download automatically - **SAVE THIS FILE SECURELY**
8. This file contains your credentials - **DO NOT commit it to git**

## Step 5: Get Service Account Email

1. In the service account details page, copy the **"Email"** address
   - It looks like: `tescon-service-account@your-project.iam.gserviceaccount.com`
2. You'll need this email in the next steps

## Step 6: Share Google Sheet with Service Account

1. Open your Google Sheet: https://docs.google.com/spreadsheets/d/15qPuy31U6Pob50l75Ie15lDhz9QNoBv5SBWqYQ9wCSY/edit
2. Click the **"Share"** button (top right)
3. Paste the service account email (from Step 5)
4. Give it **"Viewer"** access (read-only is enough)
5. Uncheck **"Notify people"** (service accounts don't need notifications)
6. Click **"Share"**

## Step 7: Create Google Drive Folder and Share

1. Go to [Google Drive](https://drive.google.com/)
2. Create a new folder: **"TESCON Processed Images"** (or your preferred name)
3. Right-click the folder → **"Share"**
4. Paste the service account email (from Step 5)
5. Give it **"Editor"** access (needs to upload files)
6. Uncheck **"Notify people"**
7. Click **"Share"**

## Step 8: Get Folder ID

1. Open the folder you just created
2. Look at the URL in your browser
3. The URL will look like: `https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j`
4. Copy the part after `/folders/` - this is your **Folder ID**
   - Example: `1a2b3c4d5e6f7g8h9i0j`

## Step 9: Get Sheet ID

1. Open your Google Sheet
2. Look at the URL: `https://docs.google.com/spreadsheets/d/15qPuy31U6Pob50l75Ie15lDhz9QNoBv5SBWqYQ9wCSY/edit`
3. Copy the part after `/d/` and before `/edit` - this is your **Sheet ID**
   - Example: `15qPuy31U6Pob50l75Ie15lDhz9QNoBv5SBWqYQ9wCSY`

## Step 10: Configure Environment Variables

### For Local Development

1. Copy the downloaded JSON file to your backend directory: `backend/google-credentials.json`
2. Add to `.env` file:

```bash
# Google Sheets Configuration
GOOGLE_SHEETS_ID=15qPuy31U6Pob50l75Ie15lDhz9QNoBv5SBWqYQ9wCSY
GOOGLE_SHEETS_TAB_NAME=Sheet1  # Or the name of your tab
GOOGLE_CREDENTIALS_PATH=google-credentials.json

# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID=1oFy8XefGQJW7rX4SApgmm-Q56tn1v3_D

# Optional: Column name overrides (if your sheet uses different column names)
# GOOGLE_SHEETS_PART_NUMBER_COL=Symbol Number
# GOOGLE_SHEETS_DESCRIPTION_COL=Description
# GOOGLE_SHEETS_LOCATION_COL=Location
# GOOGLE_SHEETS_ITEM_NOTE_COL=Item Note
```

### For Render Deployment

1. **Option A: Base64 Encode JSON** (Recommended)
   ```bash
   # On your local machine, encode the JSON file:
   base64 -i google-credentials.json
   # Copy the output
   ```
   
   In Render dashboard:
   - Go to your service → Environment
   - Add variable: `GOOGLE_CREDENTIALS_JSON` = (paste base64 string)
   - The code will decode it automatically

2. **Option B: Use Render Secrets** (Alternative)
   - Upload the JSON file as a secret
   - Reference it in environment variables

3. Add all other environment variables in Render:
   - `GOOGLE_SHEETS_ID`
   - `GOOGLE_SHEETS_TAB_NAME`
   - `GOOGLE_DRIVE_FOLDER_ID`
   - (Optional column overrides)

## Step 11: Verify Setup

1. Start your backend server
2. Check the logs - you should see:
   - `✓ Google Sheets API configured successfully`
   - `✓ Google Drive API configured successfully`
3. Test the health endpoint: `GET /health`
4. Test part lookup: `GET /api/parts/{part_number}`

## Troubleshooting

### Error: "Permission denied" or "Access denied"

- **Solution**: Make sure you shared both the Google Sheet AND the Drive folder with the service account email
- Double-check the email address is correct (no typos)

### Error: "API not enabled"

- **Solution**: Go back to Step 2 and ensure both APIs are enabled
- Wait a few minutes after enabling (propagation delay)

### Error: "Invalid credentials"

- **Solution**: 
  - Verify the JSON file is correct
  - Check that `GOOGLE_CREDENTIALS_PATH` points to the right file
  - For Render: Verify base64 encoding is correct

### Error: "Sheet not found"

- **Solution**: 
  - Verify `GOOGLE_SHEETS_ID` is correct
  - Check that the sheet is shared with service account
  - Verify `GOOGLE_SHEETS_TAB_NAME` matches your tab name exactly

### Error: "Folder not found"

- **Solution**:
  - Verify `GOOGLE_DRIVE_FOLDER_ID` is correct
  - Check that the folder is shared with service account
  - Make sure service account has "Editor" access (not just "Viewer")

### Rate Limiting

- Google Sheets API: 100 requests per 100 seconds per user
- Google Drive API: 1000 requests per 100 seconds per user
- If you hit limits, the system will retry with exponential backoff

## Security Best Practices

1. **Never commit credentials to git**
   - Add `google-credentials.json` to `.gitignore`
   - Use environment variables in production

2. **Use service account (not OAuth)**
   - Service accounts are better for server-to-server communication
   - No user interaction required

3. **Limit permissions**
   - Service account only needs:
     - Read access to Google Sheet
     - Write access to specific Drive folder
   - Don't give it broader access

4. **Rotate keys periodically**
   - Create new keys every 6-12 months
   - Delete old keys after updating

## Next Steps

After completing this setup:
1. Your backend can now read from Google Sheets
2. Processed images will be saved to Google Drive
3. Part lookup will work in real-time
4. Duplicate checking will work automatically

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Google Cloud Console logs
3. Check backend application logs
4. Verify all environment variables are set correctly
