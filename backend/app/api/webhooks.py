"""Webhook endpoints for external services."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.logging import setup_logger

router = APIRouter()
logger = setup_logger("webhooks")


@router.post("/jobs/complete")
async def job_complete_webhook(request: Request):
    """
    Webhook endpoint for GitHub Actions to notify when a job is complete.
    
    Expected payload:
    {
        "job_id": "job_123",
        "status": "completed",
        "processor": "github_actions",
        "processed_count": 5
    }
    """
    try:
        payload = await request.json()
        job_id = payload.get('job_id')
        status = payload.get('status')
        processor = payload.get('processor')
        processed_count = payload.get('processed_count', 0)
        
        logger.info(f"Job completion webhook received: {job_id} - {status} ({processed_count} images)")
        logger.info(f"Processor: {processor}")
        
        # You can add additional logic here:
        # - Update database
        # - Send notifications
        # - Trigger downstream processes
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Job {job_id} completion acknowledged",
                "job_id": job_id
            }
        )
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )
