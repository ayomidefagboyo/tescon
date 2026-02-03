# 🚀 Kaggle Enhanced REMBG Setup Guide

This guide will help you set up Kaggle for daily batch processing of your 69,000 images, saving $6,900 vs PicWish API.

## 📦 Step 1: Upload Your Code Package

### 1.1 Create Kaggle Dataset
```bash
1. Go to https://kaggle.com/datasets
2. Click "New Dataset"
3. Upload the file: kaggle_enhanced_rembg_package.zip
4. Title: "Enhanced REMBG Processor"
5. Description: "Background removal processor with 98% cost savings"
6. Make it PRIVATE
7. Click "Create"
```

## 🔧 Step 2: Create Processing Notebook

### 2.1 Create New Notebook
```bash
1. Go to https://kaggle.com/code
2. Click "New Notebook"
3. Title: "Daily Enhanced REMBG Processor"
4. Type: Notebook (Python)
5. IMPORTANT: Set to CPU only (not GPU)
6. Click "Create"
```

### 2.2 Import Your Dataset
```python
# In first cell of Kaggle notebook:

# Import your uploaded dataset
import os
import zipfile

# Extract your Enhanced REMBG code
with zipfile.ZipFile('/kaggle/input/enhanced-rembg-processor/kaggle_enhanced_rembg_package.zip', 'r') as zip_ref:
    zip_ref.extractall('/kaggle/working')

# Add to Python path
import sys
sys.path.append('/kaggle/working')

print("✅ Enhanced REMBG code extracted and ready!")
```

## 🔑 Step 3: Configure R2 Credentials

### 3.1 Add Secrets in Kaggle
```bash
1. In your Kaggle notebook, click "Add Data" → "Secrets"
2. Add these secrets:
   - R2_ENDPOINT: your-account.r2.cloudflarestorage.com
   - R2_ACCESS_KEY: your_r2_access_key
   - R2_SECRET_KEY: your_r2_secret_key
   - R2_BUCKET: your_bucket_name
   - RENDER_WEBHOOK: https://your-app.onrender.com/api/jobs/complete
```

### 3.2 Use Secrets in Code
```python
# In notebook cell:
import os
from kaggle_secrets import UserSecretsClient

user_secrets = UserSecretsClient()

# Get R2 credentials from Kaggle secrets
R2_ENDPOINT = f"https://{user_secrets.get_secret('R2_ENDPOINT')}"
R2_ACCESS_KEY = user_secrets.get_secret('R2_ACCESS_KEY')
R2_SECRET_KEY = user_secrets.get_secret('R2_SECRET_KEY')
R2_BUCKET = user_secrets.get_secret('R2_BUCKET')
RENDER_WEBHOOK = user_secrets.get_secret('RENDER_WEBHOOK')

print("✅ R2 credentials loaded from secrets")
```

## 🎯 Step 4: Main Processing Script

### 4.1 Copy Main Processor Code
Copy this into a new cell in your Kaggle notebook:

```python
# Install dependencies
!pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
!pip install rembg opencv-python-headless pillow boto3

# Import all necessary modules
import boto3
import zipfile
from pathlib import Path
from datetime import datetime
import time
import requests

# Import your Enhanced REMBG modules
from app.processing.rembg_processor import process_image, initialize_processor
from app.storage.local_storage import LocalStorage
from app.utils.filename_parser import parse_filename

print("🚀 Enhanced REMBG Daily Processor Ready!")
print("💰 Saving $6,900 vs PicWish API")
```

### 4.2 Add Processing Functions
```python
# Initialize R2 client
r2 = boto3.client('s3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

def download_daily_images(job_id):
    """Download today's raw images from R2."""
    print(f"📥 Downloading images for job: {job_id}")

    raw_images = []

    try:
        response = r2.list_objects_v2(
            Bucket=R2_BUCKET,
            Prefix=f'raw_images/{job_id}/'
        )

        for obj in response.get('Contents', []):
            key = obj['Key']
            image_data = r2.get_object(Bucket=R2_BUCKET, Key=key)['Body'].read()

            # Extract symbol number and filename from path
            path_parts = Path(key).parts
            if len(path_parts) >= 3:
                symbol_number = path_parts[2]
                filename = path_parts[3]

                raw_images.append({
                    'bytes': image_data,
                    'filename': filename,
                    'symbol_number': symbol_number
                })

        print(f"✅ Downloaded {len(raw_images)} images")
        return raw_images

    except Exception as e:
        print(f"❌ Error downloading: {e}")
        return []

def process_daily_batch(job_id, image_data_list):
    """Process images with Enhanced REMBG."""
    print(f"🎨 Processing {len(image_data_list)} images...")

    # Initialize Enhanced REMBG
    initialize_processor()

    # Create local storage
    local_storage = LocalStorage(
        upload_dir="/kaggle/working/uploads",
        processed_dir="/kaggle/working/processed"
    )

    processed_files = []
    start_time = time.time()

    for i, image_data in enumerate(image_data_list):
        try:
            # Process with Enhanced REMBG CPU
            processed_buffer = process_image(
                image_data['bytes'],
                output_format="PNG",
                white_background=True,
                optimization_level="cost"
            )

            # Parse filename for symbol number
            parsed = parse_filename(image_data['filename'])
            symbol_number = parsed.symbol_number if parsed.is_valid else image_data.get('symbol_number')

            # Save with same folder structure
            original_name = image_data['filename'].rsplit('.', 1)[0]
            processed_filename = f"{original_name}.png"

            file_path = local_storage.save_processed(
                processed_buffer.read(),
                processed_filename,
                job_id,
                symbol_number=symbol_number
            )

            processed_files.append(file_path)

            # Progress update
            if i % 50 == 0:
                elapsed = time.time() - start_time
                print(f"    📊 Progress: {i+1}/{len(image_data_list)}")

        except Exception as e:
            print(f"    ❌ Failed: {image_data['filename']} - {str(e)}")

    print(f"✅ Processing complete: {len(processed_files)} images")
    return processed_files

def upload_processed_to_r2(job_id, processed_files):
    """Upload processed images back to R2."""
    print(f"📤 Uploading {len(processed_files)} processed images...")

    base_path = Path("/kaggle/working/processed")

    for file_path in processed_files:
        try:
            local_file_path = base_path / file_path

            if local_file_path.exists():
                r2_key = f"processed_images/{file_path}"

                with open(local_file_path, 'rb') as f:
                    r2.put_object(
                        Bucket=R2_BUCKET,
                        Key=r2_key,
                        Body=f.read()
                    )
        except Exception as e:
            print(f"❌ Upload failed: {file_path}")

    print(f"✅ Upload complete")

def create_zip_and_notify(job_id):
    """Create ZIP and notify Render."""
    print("📦 Creating ZIP file...")

    local_storage = LocalStorage(processed_dir="/kaggle/working/processed")

    # Get all processed files
    processed_files = []
    job_dir = Path(f"/kaggle/working/processed/{job_id}")

    if job_dir.exists():
        for file_path in job_dir.rglob("*.png"):
            relative_path = file_path.relative_to(job_dir.parent)
            processed_files.append(str(relative_path))

    if processed_files:
        # Create ZIP with preserved folder structure
        zip_path = local_storage.create_zip(
            processed_files,
            f"processed_{job_id}.zip",
            job_id,
            preserve_structure=True
        )

        # Upload ZIP to R2
        with open(zip_path, 'rb') as f:
            r2.put_object(
                Bucket=R2_BUCKET,
                Key=f"processed_images/{job_id}/processed_{job_id}.zip",
                Body=f.read()
            )

        print(f"✅ ZIP created and uploaded")

    # Notify Render
    try:
        response = requests.post(RENDER_WEBHOOK,
            json={'job_id': job_id, 'status': 'completed'},
            timeout=30)
        print(f"✅ Render notified")
    except:
        print("⚠️ Failed to notify Render")
```

### 4.3 Main Processing Function
```python
def process_daily_job(job_id):
    """Main processing pipeline."""

    print("="*60)
    print(f"🚀 ENHANCED REMBG DAILY PROCESSING")
    print(f"💼 Job ID: {job_id}")
    print(f"💰 Saving $6,900 vs PicWish API")
    print("="*60)

    # Step 1: Download images
    image_data_list = download_daily_images(job_id)

    if not image_data_list:
        print("❌ No images found")
        return

    # Step 2: Process images
    processed_files = process_daily_batch(job_id, image_data_list)

    # Step 3: Upload processed images
    upload_processed_to_r2(job_id, processed_files)

    # Step 4: Create ZIP and notify
    create_zip_and_notify(job_id)

    print("="*60)
    print("🎉 DAILY PROCESSING COMPLETE!")
    print(f"📊 Processed: {len(processed_files)} images")
    print(f"💰 Cost: $0")
    print("="*60)

# Run processing for today
today_job = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
process_daily_job(today_job)
```

## 🧪 Step 5: Testing Your Setup

### 5.1 Test with Sample Data
```python
# Create test images for validation
import io
from PIL import Image

def create_test_job():
    """Create test images and upload to R2 for testing."""

    test_job_id = f"test_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Create 3 test images
    test_images = []
    for i in range(3):
        # Create simple test image
        img = Image.new('RGB', (512, 512), color=(100, 150, 200))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')

        test_images.append({
            'filename': f'58020640_{i+1}_test.png',
            'symbol_number': '58020640',
            'bytes': buffer.getvalue()
        })

    # Upload test images to R2
    for img_data in test_images:
        r2_key = f"raw_images/{test_job_id}/{img_data['symbol_number']}/{img_data['filename']}"

        r2.put_object(
            Bucket=R2_BUCKET,
            Key=r2_key,
            Body=img_data['bytes']
        )

    print(f"✅ Test job created: {test_job_id}")
    return test_job_id

# Run test
test_job = create_test_job()
process_daily_job(test_job)
```

## ⚙️ Step 6: Automation Options

### 6.1 Manual Daily Trigger
```bash
1. Visit your Kaggle notebook daily at 6 PM
2. Change job_id to today's format
3. Click "Run All"
4. Let it run for 2 hours
5. Check R2 for processed images
```

### 6.2 Semi-Automated with Webhooks
Add this to your Render app to trigger Kaggle:

```python
# In your Render app - add new route
@app.post("/api/trigger-processing")
async def trigger_daily_processing():
    """Trigger Kaggle processing via webhook."""

    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Option A: Use Kaggle API (if available)
    # kaggle_api.trigger_notebook(notebook_url, params={'job_id': job_id})

    # Option B: Manual trigger notification
    print(f"🚀 Ready for processing: {job_id}")

    return {"message": f"Ready for Kaggle processing: {job_id}"}
```

### 6.3 Full Automation (Advanced)
```python
# Use GitHub Actions or similar to trigger Kaggle
# This requires Kaggle API setup (more complex)

# .github/workflows/daily-processing.yml
name: Daily Image Processing
on:
  schedule:
    - cron: '0 18 * * *'  # 6 PM daily
jobs:
  trigger-kaggle:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Kaggle Notebook
        run: |
          # Call Kaggle API to run your notebook
          curl -X POST "https://www.kaggle.com/api/v1/kernels/push" \
            -H "Authorization: Bearer ${{ secrets.KAGGLE_TOKEN }}" \
            -d '{"id": "your-notebook-id", "enable_gpu": false}'
```

## 📊 Step 7: Monitoring & Maintenance

### 7.1 Check Processing Results
```python
# Add this to monitor your daily processing
def check_processing_status(job_id):
    """Check if processing completed successfully."""

    try:
        # Check if ZIP file exists in R2
        r2.head_object(
            Bucket=R2_BUCKET,
            Key=f"processed_images/{job_id}/processed_{job_id}.zip"
        )

        # Count processed images
        response = r2.list_objects_v2(
            Bucket=R2_BUCKET,
            Prefix=f'processed_images/{job_id}/'
        )

        image_count = len([obj for obj in response.get('Contents', []) if obj['Key'].endswith('.png')])

        print(f"✅ Job {job_id} complete: {image_count} images processed")
        return True

    except:
        print(f"❌ Job {job_id} not complete")
        return False

# Usage
check_processing_status("job_20250125_143022")
```

### 7.2 Error Handling
```python
# Add to your main processing function
def safe_process_daily_job(job_id, max_retries=3):
    """Process with retry logic."""

    for attempt in range(max_retries):
        try:
            process_daily_job(job_id)
            return True
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("🔄 Retrying in 5 minutes...")
                time.sleep(300)  # Wait 5 minutes
            else:
                print("❌ All attempts failed")
                return False
```

## 🎯 Step 8: Daily Workflow

### Your Complete Daily Process:
```
5:30 PM: Field workers finish uploading photos
6:00 PM: You trigger Kaggle notebook (or automated)
6:00-8:00 PM: Kaggle processes 900 images with Enhanced REMBG
8:00 PM: Processed images available in R2
8:00 PM: Render receives completion notification
Next morning: Workers download processed images

Cost: $0 per day
Savings vs PicWish: $90 per day ($6,900 total)
```

## ⚠️ Important Notes

1. **Kaggle Session Limits**: 9 hours max, but your 2-hour processing fits perfectly
2. **Background Execution**: Enable this so you can close browser
3. **Error Recovery**: Always check logs if processing fails
4. **R2 Storage**: Monitor your storage usage and costs
5. **Render Integration**: Test webhook notifications work properly

## 🆘 Troubleshooting

### Common Issues:
- **"Module not found"**: Check your code extraction step
- **"R2 credentials invalid"**: Verify secrets are set correctly
- **"Processing too slow"**: Normal for CPU, ~8 seconds per image
- **"Kaggle session expires"**: Enable background execution
- **"Out of memory"**: Reduce batch size in processing loop

### Getting Help:
1. Check Kaggle notebook logs for detailed errors
2. Test R2 connection independently
3. Verify your Enhanced REMBG works locally first
4. Check Render webhook receives notifications

## 🎉 Success Metrics

When working correctly, you should see:
- ✅ 900 images processed per day
- ✅ 2-hour processing time in Kaggle
- ✅ Same folder structure as before
- ✅ ZIP files created with symbol numbers
- ✅ $0 processing cost vs $90 with PicWish
- ✅ $6,900 total savings over 77 days

**You now have a complete $6,900 cost-saving solution!** 🚀

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create Kaggle notebook setup guide", "status": "completed", "activeForm": "Creating Kaggle notebook setup guide"}, {"content": "Prepare code files for Kaggle upload", "status": "completed", "activeForm": "Preparing code files for Kaggle upload"}, {"content": "Configure R2 integration in Kaggle", "status": "completed", "activeForm": "Configuring R2 integration in Kaggle"}, {"content": "Test sample batch processing", "status": "in_progress", "activeForm": "Testing sample batch processing"}, {"content": "Create automation trigger system", "status": "pending", "activeForm": "Creating automation trigger system"}]