"""FastAPI application entry point."""
import os
from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from .env file
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.models import HealthResponse
from app.api.routes import router

app = FastAPI(title="Tescon Image Processing API", version="1.0.0")

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Internal tool - allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Include retry routes
from app.api.retry import router as retry_router
app.include_router(retry_router, prefix="/api")

# Include validation routes
from app.api.validation import router as validation_router
app.include_router(validation_router, prefix="/api")

# Include export routes
from app.api.export import router as export_router
app.include_router(export_router, prefix="/api")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from app.processing.lightweight_processor import is_model_loaded
    
    return HealthResponse(
        status="healthy",
        gpu_available=False,  # API-based, no GPU needed
        model_loaded=True
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__}
    )


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    # Verify Enhanced REMBG availability
    from app.processing.lightweight_processor import is_model_loaded
    from app.api.jobs import job_manager
    from app.storage.local_storage import LocalStorage
    from app.services.excel_service import get_excel_parts_service
    from app.services.parts_tracker import get_parts_tracker
    import asyncio
    from pathlib import Path

    if is_model_loaded():
        print("✓ Lightweight processor configured successfully")
        print("✓ All processing will be handled via Kaggle Enhanced REMBG")
    else:
        print("⚠ Warning: Processor not available.")

    # Load Excel file if it exists
    excel_file_path = Path(__file__).parent.parent / "EGTL_FINAL_23033_CLEANED.xlsx"
    if excel_file_path.exists():
        try:
            excel_service = get_excel_parts_service()
            success = excel_service.load_excel_file(str(excel_file_path), sheet_name="Sheet1")
            if success:
                stats = excel_service.get_stats()
                print(f"✓ Excel catalog loaded: {stats['total_parts']} parts")

                # Update parts tracker with total count
                tracker = get_parts_tracker()
                tracker.set_total_parts(stats['total_parts'])
            else:
                print("⚠ Warning: Failed to load Excel catalog file")
        except Exception as e:
            print(f"⚠ Warning: Error loading Excel catalog: {e}")
    else:
        print("⚠ Warning: Excel catalog file not found. Upload via /api/excel/upload endpoint.")

    # Start background cleanup tasks
    async def cleanup_task():
        """Periodic cleanup of old jobs and files."""
        while True:
            await asyncio.sleep(3600)  # Run every hour
            try:
                job_manager.cleanup_old_jobs(days=7)
                storage = LocalStorage()
                storage.cleanup_old_files()
            except Exception as e:
                print(f"Cleanup error: {e}")

    asyncio.create_task(cleanup_task())

    # Start Kaggle batch processing service
    from app.services.kaggle_batch_service import start_kaggle_batch_service
    asyncio.create_task(start_kaggle_batch_service())

