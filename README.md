# Tescon - Internal Image Background Removal Tool

An internal tool for automatically processing spare-part images for SharePoint catalog upload. Removes backgrounds, standardizes to white backgrounds, validates filenames, and organizes by symbol number.

## Features

### Core Processing
- **Background Removal**: Uses PicWish API for high-quality background removal
- **White Background**: Automatically composites processed images onto white backgrounds
- **Image Compression**: User-controlled compression with quality presets
- **Multiple Formats**: Output as PNG or JPEG

### SharePoint Integration
- **Filename Validation**: Enforces `PartNumber_ViewNumber_Location.jpg` format
- **On-the-Spot Renaming**: Fix invalid filenames before processing
- **Auto-Folder Organization**: Creates folders by symbol number automatically
- **Export Structure**: `/PartNumber/PartNumber_view1_Location.jpg`
- **Pre-Export Validation**: Checks for missing views and corrupted images

### Bulk Processing
- **Large Volume Support**: Handles 50,000+ images with intelligent batching (500 per batch)
- **Concurrent Processing**: Configurable concurrent API requests (default: 10)
- **Progress Tracking**: Real-time progress updates with detailed job status
- **Retry Failed Images**: One-click retry for failed images
- **Resumable Jobs**: Pause and resume batch processing

### User Experience
- **Filename Validation Summary**: Shows valid/invalid counts, unique parts
- **Visual Guides**: Built-in naming convention help
- **Error Handling**: Clear error messages for non-technical users
- **No Scrolling**: All controls visible in viewport

## Naming Convention

All images must follow this format:

```
PartNumber_ViewNumber_Description.ext
```

### Example
```
58802935_1_BEARING.jpg
74452282_2_FAN TYPE.jpg
12345678_3_PUMP ASSEMBLY.jpg
```

Where:
- **PartNumber**: Part/item number (used for folder organization)
- **ViewNumber**: Image angle (1, 2, 3...)
- **Description**: Part type/description (spaces allowed, e.g., BEARING, FAN TYPE)

## Architecture

- **Backend**: FastAPI (Python) with PicWish API integration
- **Frontend**: React + TypeScript with Vite
- **Storage**: Local filesystem with part-number folder organization
- **Processing**: PicWish API (cloud-based background removal)
- **Database**: SQLite for job persistence

## Quick Start

### Prerequisites

- Docker and Docker Compose
- PicWish API key (get one at https://picwish.com/api-pricing)

### Running with Docker Compose

```bash
# Set your API key in environment
export PICWISH_API_KEY=your_api_key_here

# Build and start services
docker-compose up --build

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Running Locally

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set your PicWish API key
export PICWISH_API_KEY=your_api_key_here

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Processing
- `POST /api/process/single` - Process single image synchronously
- `POST /api/process/bulk` - Process multiple images asynchronously (with batching)
  - Parameters: `compression_quality`, `max_dimension`

### Validation
- `POST /api/validate/filenames` - Validate batch of filenames
- `POST /api/validate/parse` - Parse single filename
- `GET /api/jobs/{job_id}/validate-export` - Validate job before export

### Jobs
- `GET /api/jobs/{job_id}` - Get job status with progress and failed images
- `GET /api/jobs/{job_id}/download` - Download processed images ZIP (organized by symbol number)
- `POST /api/jobs/{job_id}/retry` - Retry failed images from a completed job

### Health
- `GET /health` - Health check

## Configuration

Environment variables (backend):

- `PICWISH_API_KEY`: **Required** - Your PicWish API key
- `UPLOAD_DIR`: Upload directory (default: `uploads`)
- `PROCESSED_DIR`: Processed images directory (default: `processed`)
- `CLEANUP_TTL_HOURS`: Hours before cleanup (default: `24`, `0` = no cleanup)
- `MAX_FILE_SIZE`: Maximum file size in MB (default: `100`)
- `BATCH_SIZE`: Images per batch for large volumes (default: `500`)
- `MAX_CONCURRENT`: Maximum concurrent API requests (default: `10`)
- `DEFAULT_COMPRESSION_QUALITY`: Default compression quality (default: `85`)
- `DEFAULT_MAX_DIMENSION`: Default max dimension (default: `2048`)

## Workflow

### 1. Upload Images
- Drag & drop or select multiple images
- System validates filenames automatically
- Shows summary: total files, valid/invalid, unique parts

### 2. Fix Invalid Names (if any)
- Click "Rename" on any invalid file
- Enter: Symbol Number, View Number, Location
- Or skip invalid files

### 3. Configure Processing
- Choose output format (PNG/JPEG)
- Enable white background
- Select compression preset:
  - **High Quality**: 95% quality, 4096px
  - **Balanced**: 85% quality, 2048px (recommended)
  - **Web Optimized**: 80% quality, 1600px
  - **Compact**: 75% quality, 1200px

### 4. Process
- Click "Process X files"
- Monitor progress in real-time
- See batch-level updates

### 5. Download
- Download ZIP with SharePoint-ready folder structure
- Structure: `/PartNumber/PartNumber_view1_Location.jpg`
- Upload folders directly to SharePoint

### 6. Handle Failures (if any)
- View failed images and errors
- Click "Retry Failed" to reprocess
- Or download successful results anyway

## Output Structure

```
processed_[job_id].zip
├── 58802935/
│   ├── 58802935_1_EG1060007.jpg
│   ├── 58802935_2_EG1060007.jpg
│   └── 58802935_3_EG1060007.jpg
├── 74452282/
│   ├── 74452282_1_EG1060007.jpg
│   └── 74452282_2_EG1060007.jpg
└── ...
```

Each part has its own folder, ready for SharePoint upload.

## Deployment

### Quick Free Deployment (Recommended)

**Deploy without Docker using free hosting:**

1. **Backend**: Deploy to [Railway.app](https://railway.app) (free $5/month credit)
   - Connect GitHub repo
   - Set root directory to `backend`
   - Add `PICWISH_API_KEY` environment variable
   - Railway auto-detects Python and deploys

2. **Frontend**: Deploy to [Vercel](https://vercel.com) (free tier)
   - Connect GitHub repo
   - Set root directory to `frontend`
   - Add `VITE_API_URL` environment variable (your Railway backend URL + `/api`)

**See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.**

### Docker Deployment (Alternative)

For internal deployment with Docker:

1. Deploy on a single VM or on-prem machine
2. Use Docker Compose for easy deployment
3. Mount volumes for persistent storage
4. Access via internal network/VPN only
5. No authentication required (internal tool)

### PicWish API Setup

1. Sign up for a PicWish account at https://picwish.com/api-pricing
2. Get your API key from the dashboard
3. Set the `PICWISH_API_KEY` environment variable:
   - In `.env` file: `PICWISH_API_KEY=your_key_here`
   - In Docker Compose: Add to `environment` section
   - Or export: `export PICWISH_API_KEY=your_key_here`

## Success Metrics

- ✅ ≥ 95% images processed without manual rework
- ✅ Zero manual folder sorting
- ✅ Consistent naming across all parts
- ✅ Processing bottleneck only at photography stage

## License

Internal use only - TESCON Engineering Solutions & Consulting Services Ltd.
