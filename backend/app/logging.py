"""Structured logging for image processing."""
import json
import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "image_filename"):
            log_data["image_filename"] = record.image_filename
        if hasattr(record, "job_id"):
            log_data["job_id"] = record.job_id
        if hasattr(record, "gpu_used"):
            log_data["gpu_used"] = record.gpu_used
        if hasattr(record, "processing_time_ms"):
            log_data["processing_time_ms"] = record.processing_time_ms
        if hasattr(record, "image_size_bytes"):
            log_data["image_size_bytes"] = record.image_size_bytes
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
        
        return json.dumps(log_data)


def setup_logging(log_dir: str = "logs", log_level: str = "INFO"):
    """
    Setup structured logging.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("tescon")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with JSON format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # File handler for errors
    error_file = log_path / "errors.log"
    file_handler = logging.FileHandler(error_file)
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    # File handler for all logs
    all_logs_file = log_path / "app.log"
    all_handler = logging.FileHandler(all_logs_file)
    all_handler.setFormatter(JSONFormatter())
    logger.addHandler(all_handler)
    
    return logger


# Global logger instance
logger = setup_logging()


def log_image_processing(
    image_filename: str,
    job_id: Optional[str] = None,
    gpu_used: bool = False,
    processing_time_ms: Optional[float] = None,
    image_size_bytes: Optional[int] = None,
    success: bool = True,
    error: Optional[str] = None
):
    """
    Log image processing event.
    
    Args:
        image_filename: Name of the processed image
        job_id: Optional job ID
        gpu_used: Whether GPU was used
        processing_time_ms: Processing time in milliseconds
        image_size_bytes: Image size in bytes
        success: Whether processing succeeded
        error: Error message if failed
    """
    level = logging.INFO if success else logging.ERROR
    
    extra = {
        "image_filename": image_filename,
        "gpu_used": gpu_used,
    }
    
    if job_id:
        extra["job_id"] = job_id
    if processing_time_ms:
        extra["processing_time_ms"] = processing_time_ms
    if image_size_bytes:
        extra["image_size_bytes"] = image_size_bytes
    if error:
        extra["error_type"] = type(error).__name__ if hasattr(error, "__name__") else "Unknown"
    
    message = f"Image processing {'succeeded' if success else 'failed'}: {image_filename}"
    if error:
        message += f" - {str(error)}"
    
    logger.log(level, message, extra=extra)


def log_gpu_metrics(gpu_available: bool, gpu_memory_used_mb: Optional[float] = None):
    """
    Log GPU usage metrics.
    
    Args:
        gpu_available: Whether GPU is available
        gpu_memory_used_mb: GPU memory used in MB
    """
    extra = {
        "gpu_available": gpu_available,
    }
    if gpu_memory_used_mb:
        extra["gpu_memory_mb"] = gpu_memory_used_mb
    
    logger.info("GPU metrics", extra=extra)

