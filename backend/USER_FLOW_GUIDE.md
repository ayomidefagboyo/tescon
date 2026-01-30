# TESCON Enhanced Background Removal - User Guide

🎯 **Process 20,000+ images with 98% cost savings using AI-powered Enhanced REMBG**

## Overview

TESCON uses **Enhanced REMBG** processing exclusively - an AI-powered background removal system that delivers professional results with massive cost savings through automated Kaggle processing.

**Cost Comparison:**
- Enhanced REMBG: $0.002 per image
- Alternative services: $0.10+ per image
- **98% cost savings for large batches**

---

## 🌐 Complete User Workflow

### Step 1: Web Interface Upload
🖥️ **From your web browser:**

1. **Access TESCON web app** at your deployed URL
2. **Navigate to image processing** section
3. **Select parts** from your Excel catalog (20,000+ parts available)
4. **Upload photos** of each part (up to 10 images per part)
5. **Configure processing options:**
   - Format: PNG (recommended) or JPEG
   - Background: White (standard for product catalogs)
   - Quality: 70-100% compression
   - Labels: Automatic part information overlay
   - View numbers: 1,2,3... for multiple angles

### Step 2: Automatic Queue Processing
⚙️ **System handles everything automatically:**

1. **Immediate upload** → Raw images stored in R2 cloud storage
2. **Job queuing** → Processing metadata created automatically
3. **Background monitoring** → Worker polls for new jobs every 5 seconds
4. **Kaggle processing** → Enhanced REMBG triggered via automated batch system
5. **Smart scheduling** → Jobs processed hourly for optimal efficiency

**Processing Timeline:**
- Upload: Instant (images stored in R2)
- Queue time: 0-60 minutes (depending on batch schedule)
- Processing: 5-15 minutes per batch
- Results: Available immediately after processing

### Step 3: Professional Results
📥 **Get your processed images:**

1. **Automatic R2 storage** → Processed images saved to cloud storage
2. **Professional product images** with:
   - ✅ Clean white backgrounds (backgrounds completely removed)
   - ✅ Part numbers and descriptions overlay
   - ✅ High-quality compression optimized for catalogs
   - ✅ Consistent naming: `PartNumber_ViewNumber_Description.png`
3. **Download options** → Access via web interface or direct R2 links
4. **Organized storage** → Images grouped by part number for easy management

---

## 🔧 Technical Architecture

### Processing Engine: Enhanced REMBG
- **AI Model**: BiRefNet + IS-Net for superior background removal
- **Processing Location**: Kaggle notebooks with GPU acceleration
- **Fallback**: CPU processing for reliability
- **Quality**: Professional-grade edge detection and refinement

### Storage: Cloudflare R2
- **Raw Images**: `raw_images/{job_id}/` folder structure
- **Job Queue**: `jobs/queued/` for processing metadata
- **Processed Results**: `processed_images/` organized by part number
- **Reliability**: Distributed cloud storage with automatic backups

### Automation: Smart Batch Processing
- **Strategy**: Hourly batches (configurable)
- **Efficiency**: Process multiple jobs together
- **Cost optimization**: Minimal Kaggle notebook usage
- **Monitoring**: Real-time job status tracking

---

## 📊 Processing Options & Features

### Image Input Requirements
- **Formats supported**: JPEG, PNG, WebP, HEIC
- **File size limit**: 100MB per image
- **Resolution**: Up to 4096×4096 pixels
- **Batch size**: 1-10 images per part
- **Background**: Any color/complexity (AI removes automatically)

### Output Specifications
- **Format**: PNG (lossless, recommended) or JPEG (smaller files)
- **Background**: Professional white background
- **Resolution**: Maintains original aspect ratio, max 4096px
- **Compression**: 70-100% quality control
- **Naming**: `{PartNumber}_{ViewNumber}_{Description}.png`

### Smart Labeling System
- **Part information overlay** automatically applied:
  - Symbol/Part number (e.g., "58020640")
  - Short description from Excel catalog
  - Long description (when available)
  - Manufacturer details
- **Label positioning**: Bottom-left (default), customizable
- **Typography**: Professional fonts with high contrast
- **Layout**: E-commerce optimized product card design

---

## 💻 Web Interface Usage

### Uploading Images
1. **Navigate to processing page** in web interface
2. **Enter part number** → System validates against Excel catalog
3. **Upload images** → Drag & drop or file selector (up to 10 images)
4. **Set view numbers** → 1,2,3... for different angles (optional)
5. **Configure options** → Format, quality, labeling preferences
6. **Submit for processing** → Job queued immediately

### Monitoring Progress
1. **Job ID provided** → Unique identifier for tracking
2. **Status checking** → Real-time updates via `/jobs/{job_id}` endpoint
3. **Progress tracking** → See total parts processed vs remaining
4. **Error handling** → Detailed error messages for failed jobs

### Downloading Results
1. **Processing completion** → Notification when batch is ready
2. **Individual downloads** → Access specific processed images
3. **Bulk download** → ZIP archive of all processed images
4. **R2 direct access** → Permanent cloud storage links

---

## 🏭 Enterprise Features

### Excel Catalog Integration
- **20,000+ parts database** → Complete parts catalog
- **Automatic validation** → Prevents processing non-existent parts
- **Smart search** → Find parts by number, description, or manufacturer
- **Auto-populated labels** → Part data automatically applied to images
- **Progress tracking** → Monitor which parts have been processed

### Batch Processing Optimization
- **Hourly batches** → Process up to hundreds of images together
- **Cost efficiency** → $40 total vs $2,000 for 20k images (98% savings)
- **Queue management** → Upload anytime, processing happens automatically
- **Scalability** → Handle enterprise-level image volumes

### Quality Control & Reliability
- **Automatic validation** → Images checked before processing
- **Retry mechanism** → Failed jobs automatically retried
- **Error tracking** → Detailed logs for troubleshooting
- **Backup storage** → Both raw and processed images preserved
- **Progress reports** → Export detailed processing statistics

---

## ⚡ Quick Start Guide

### First Time Setup
1. **Access web interface** at your deployment URL
2. **Verify Excel catalog** is loaded (should show 20,000+ parts)
3. **Test with sample part** → Try processing 1-2 images first
4. **Check results** → Verify quality and labeling meets requirements

### For Large Batches (100+ parts)
1. **Plan your upload schedule** → Spread uploads throughout day
2. **Use consistent naming** → Include view numbers for multiple angles
3. **Monitor processing queue** → Check progress via tracking endpoints
4. **Download in batches** → Use ZIP download for large volumes

### Best Practices
- **Upload during off-peak hours** → Faster processing in smaller queues
- **Use PNG format** → Best quality for product catalogs
- **Include multiple angles** → Views 1,2,3 for comprehensive documentation
- **Verify part numbers** → System validates against Excel catalog
- **Keep originals** → Raw images preserved as backup

---

## 📈 Cost Analysis

| Volume | Processing Cost | Traditional Cost | Savings |
|--------|----------------|------------------|---------|
| 10 images | $0.02 | $1.00 | $0.98 (98%) |
| 100 images | $0.20 | $10.00 | $9.80 (98%) |
| 1,000 images | $2.00 | $100.00 | $98.00 (98%) |
| 10,000 images | $20.00 | $1,000.00 | $980.00 (98%) |
| **20,000 images** | **$40.00** | **$2,000.00** | **$1,960.00 (98%)** |

**Annual savings for 50k+ image processing: $4,900+**

---

## 🛠️ System Requirements

### Web Interface
- **Browser**: Chrome, Firefox, Safari, Edge (modern versions)
- **Connection**: Stable internet for uploads
- **Storage**: Minimal local storage needed (cloud-based processing)

### Image Requirements
- **File formats**: JPEG, PNG, WebP, HEIC
- **Size limit**: 100MB per image
- **Resolution**: Recommended 1920×1080 or higher for best results
- **Background**: Any complexity (AI handles all background types)

### Network Requirements
- **Upload bandwidth**: Recommended 10+ Mbps for multiple image uploads
- **Download bandwidth**: 5+ Mbps for processed image downloads
- **Latency**: Processing happens in cloud, not affected by local network

---

## 🔍 Monitoring & Troubleshooting

### Real-Time Monitoring
- **Job status endpoint**: `/api/jobs/{job_id}` for individual job tracking
- **Progress tracking**: `/api/tracker/progress` for overall statistics
- **Queue monitoring**: `/api/debug/env` for system health checks

### Common Issues & Solutions

**Q: Images not processing / stuck in queue?**
A: Check Kaggle batch service status. Processing happens hourly, wait 60 minutes maximum.

**Q: Poor background removal quality?**
A: Ensure good lighting and clear part visibility. AI works best with well-lit, focused images.

**Q: Part not found in catalog?**
A: Verify part number exists in Excel catalog. Use search endpoint to find correct number.

**Q: Upload failing?**
A: Check file size (max 100MB) and format (JPEG/PNG supported). Verify network connectivity.

### Support Resources
- **System logs**: Available via web interface for administrators
- **Error tracking**: Detailed error messages for failed processing
- **Performance metrics**: Processing times and success rates monitored

---

## 🎯 Key Benefits

### Cost Efficiency
- **98% cost reduction** compared to traditional API services
- **Predictable pricing** → $0.002 per image, no surprises
- **No subscription fees** → Pay only for processing used

### Professional Quality
- **AI-powered background removal** using state-of-the-art BiRefNet models
- **Consistent white backgrounds** perfect for product catalogs
- **Professional labeling** with part numbers and descriptions
- **High-resolution output** maintaining image quality

### Enterprise Scale
- **Handle 20,000+ images** efficiently through batch processing
- **Automatic processing** → Upload and forget, results delivered automatically
- **Reliable storage** → Cloudflare R2 cloud storage with 99.9% uptime
- **Progress tracking** → Monitor processing across your entire catalog

### Simple Workflow
- **Web-based interface** → No software installation required
- **Automatic validation** → System prevents invalid part numbers
- **Organized results** → Images automatically named and organized
- **Download options** → Individual files or bulk ZIP downloads

---

*🚀 Transform your product catalog with professional AI-powered image processing at 98% cost savings!*