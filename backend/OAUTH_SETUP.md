# Google Drive OAuth Setup

This guide walks you through setting up OAuth authentication for Google Drive to solve the storage quota issue.

## Why OAuth?

Service accounts don't have storage quota, causing the error:
```
Service Accounts do not have storage quota. Leverage shared drives or use OAuth delegation instead.
```

OAuth uses your personal Google account which has storage space.

## Step 1: Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your existing project: `tescon-484514`
3. Go to **"APIs & Services"** → **"Credentials"**
4. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
5. If prompted, configure OAuth consent screen first:
   - Application type: **Internal** (or External if needed)
   - Application name: **TESCON Image Processor**
   - User support email: Your email
   - Developer contact: Your email
   - Save and continue through all screens
6. For OAuth client ID:
   - Application type: **Desktop application**
   - Name: **TESCON Desktop Client**
7. Click **"Create"**
8. Download the JSON file and save it as `oauth_credentials.json` in the backend directory

## Step 2: Update Environment

The `.env` file has been updated to use OAuth:
```bash
# Google Drive Authentication
# OAuth (for personal Google account)
GOOGLE_OAUTH_CREDENTIALS_PATH=oauth_credentials.json
GOOGLE_TOKEN_PATH=token.pickle

# Google Drive folder (same as before)
GOOGLE_DRIVE_FOLDER_ID=1oFy8XefGQJW7rX4SApgmm-Q56tn1v3_D
```

## Step 3: First Time OAuth Setup

When you first try to process images, the system will:

1. Open a browser window for OAuth consent
2. Ask you to sign in with your Google account (the one that owns the folder)
3. Grant permission to access Google Drive
4. Save the token for future use

## Step 4: Test the Setup

1. Make sure `oauth_credentials.json` exists in `/Users/admin/tescon/backend/`
2. Try processing a part with images
3. Complete the OAuth flow when prompted
4. Future requests will use the saved token automatically

## Files Needed

- `oauth_credentials.json` - OAuth client secrets (download from Google Cloud Console)
- `token.pickle` - Saved OAuth token (created automatically after first auth)

## Security Notes

- `oauth_credentials.json` contains client secrets - keep it secure
- `token.pickle` contains your access token - don't commit to git
- Tokens automatically refresh when needed

## Troubleshooting

If you get authentication errors:
1. Delete `token.pickle` to force re-authentication
2. Make sure the folder `1oFy8XefGQJW7rX4SApgmm-Q56tn1v3_D` is owned by the Google account you're using
3. Check that the OAuth client is configured for "Desktop application"