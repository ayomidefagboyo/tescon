#!/bin/bash
# Startup script for Railway/Render deployment
# Uses PORT environment variable if available, otherwise defaults to 8000

PORT=${PORT:-8000}
uvicorn app.main:app --host 0.0.0.0 --port $PORT
