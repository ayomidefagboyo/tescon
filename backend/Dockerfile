FROM python:3.11-slim

# Install system dependencies for enhanced REMBG processing
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu118 && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download REMBG models to avoid runtime downloads
RUN python -c "from rembg import remove, new_session; import requests; \
    session = new_session('birefnet-general'); \
    print('BiRefNet model downloaded'); \
    session2 = new_session('isnet-general-use'); \
    print('IS-Net model downloaded')"

# Copy application code
COPY . .

# Create directories for uploads and processed files
RUN mkdir -p uploads processed

# Set environment variables for optimized GPU usage
ENV CUDA_VISIBLE_DEVICES=0
ENV TORCH_CUDA_ARCH_LIST="6.0 6.1 7.0 7.5 8.0 8.6+PTX"
ENV TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1

# Optimize for production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

