# Tescon - Internal Image Background Removal Tool

An internal tool for automatically removing backgrounds from spare-part images and standardizing them with white backgrounds.

## Features

- **Single Image Processing**: Upload and process one image at a time with immediate download
- **Bulk Processing**: Upload multiple images or a ZIP file for async batch processing
- **Large Volume Support**: Handles 50,000+ images with intelligent batching (500 images per batch)
- **Concurrent Processing**: Configurable concurrent API requests (default: 10) for faster throughput
- **Background Removal**: Uses PicWish API for high-quality background removal
- **White Background**: Automatically composites processed images onto white backgrounds
- **Multiple Formats**: Output as PNG or JPEG
- **Retry Failed Images**: One-click retry for failed images from completed jobs
- **Progress Tracking**: Real-time progress updates with detailed job status
- **Failure Logging**: Comprehensive logging of failed images with error messages
- **API-Based**: Cloud-based processing, no local GPU required

## Architecture

- **Backend**: FastAPI (Python) with PicWish API integration
- **Frontend**: React + TypeScript with Vite
- **Storage**: Local filesystem (extensible to S3/NAS)
- **Processing**: PicWish API (cloud-based background removal)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- PicWish API key (get one at https://picwish.com/api-pricing)

### Running with Docker Compose

```bash
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

- `POST /api/process/single` - Process single image synchronously
- `POST /api/process/bulk` - Process multiple images asynchronously (with batching)
- `GET /api/jobs/{job_id}` - Get job status with progress and failed images
- `GET /api/jobs/{job_id}/download` - Download processed images ZIP
- `POST /api/jobs/{job_id}/retry` - Retry failed images from a completed job
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

## Deployment

For internal deployment:

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

## Week 2 Enhancements (Completed)

- ✅ Structured error logging with image metadata
- ✅ Retry logic for failed images (with exponential backoff)
- ✅ Persistent job storage (SQLite)
- ✅ API rate limit handling
- ✅ Batch processing for large volumes (50,000+ images)
- ✅ Concurrent processing with configurable limits
- ✅ Retry failed images endpoint and UI
- ✅ Comprehensive failure tracking and logging

## License

Internal use only.

