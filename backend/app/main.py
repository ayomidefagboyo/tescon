"""FastAPI application entry point."""
import os
from fastapi import FastAPI
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


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from app.processing.picwish_processor import check_api_available, is_model_loaded
    
    return HealthResponse(
        status="healthy",
        gpu_available=False,  # API-based, no GPU needed
        model_loaded=is_model_loaded()
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
    # Verify PicWish API availability
    from app.processing.picwish_processor import check_api_available
    from app.api.jobs import job_manager
    from app.storage.local_storage import LocalStorage
    import asyncio
    
    if check_api_available():
        print("✓ PicWish API configured successfully")
    else:
        print("⚠ Warning: PicWish API key not configured. Set PICWISH_API_KEY environment variable.")
    
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

