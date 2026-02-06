#!/bin/bash

# Sync Processed Images to SharePoint
# 1. Download images from R2 to local 'downloads' folder
# 2. Upload images from 'downloads' to SharePoint

# Go to project root (assuming script is in backend/)
cd "$(dirname "$0")/.." || exit

echo "🚀 Starting Synchronization..."

# Step 1: Download
echo "⬇️  Step 1: Downloading images from R2..."
python3 backend/download_processed_images.py
if [ $? -ne 0 ]; then
    echo "❌ Download failed."
    exit 1
fi

# Step 2: Upload
echo "⬆️  Step 2: Uploading images to SharePoint..."
python3 backend/upload_to_sharepoint.py
if [ $? -ne 0 ]; then
    echo "❌ Upload failed."
    exit 1
fi

echo "✅ Synchronization Complete!"
