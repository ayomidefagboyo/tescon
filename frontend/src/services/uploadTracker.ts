/** Upload status tracking service with localStorage persistence */

export interface UploadAttempt {
  id: string;
  partNumber: string;
  timestamp: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  jobId?: string;
  files: File[];
  viewNumbers?: number[];
  retryCount: number;
  maxRetries: number;
  lastError?: string;
  completedAt?: number;
}

export interface UploadOptions {
  format?: "PNG" | "JPEG" | "JPG";
  whiteBackground?: boolean;
  compressionQuality?: number;
  maxDimension?: number;
  addLabel?: boolean;
  labelPosition?: "bottom-left" | "bottom-right" | "top-left" | "top-right" | "bottom-center";
}

class UploadTracker {
  private storageKey = 'tescon_upload_queue';
  private maxRetries = 3;
  private retryDelays = [500, 2000, 8000]; // 0.5s, 2s, 8s (faster retries for network issues)

  // Get all uploads from localStorage
  private getUploads(): UploadAttempt[] {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (!stored) return [];

      const uploads = JSON.parse(stored) as UploadAttempt[];

      // Validate the parsed data structure
      if (!Array.isArray(uploads)) {
        console.warn('Upload queue data is not an array, clearing corrupted data');
        localStorage.removeItem(this.storageKey);
        return [];
      }

      // Convert File objects back (they don't serialize well)
      return uploads.map(upload => ({
        ...upload,
        files: [] // Files will be re-added when retrying
      }));
    } catch (error) {
      console.warn('Failed to parse upload queue, clearing corrupted data:', error);
      // Clear corrupted data to prevent future errors
      localStorage.removeItem(this.storageKey);
      return [];
    }
  }

  // Save uploads to localStorage
  private saveUploads(uploads: UploadAttempt[]): void {
    try {
      // Don't store File objects (they're not serializable)
      const serializable = uploads.map(upload => ({
        ...upload,
        files: upload.files.map(f => ({ name: f.name, size: f.size, type: f.type }))
      }));
      localStorage.setItem(this.storageKey, JSON.stringify(serializable));
    } catch (error) {
      console.warn('Failed to save upload queue:', error);
    }
  }

  // Add new upload attempt
  addUpload(
    partNumber: string,
    files: File[],
    viewNumbers?: number[],
    options?: UploadOptions
  ): string {
    const uploads = this.getUploads();
    const id = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    const upload: UploadAttempt = {
      id,
      partNumber,
      timestamp: Date.now(),
      status: 'pending',
      files,
      viewNumbers,
      retryCount: 0,
      maxRetries: this.maxRetries,
    };

    uploads.push(upload);
    this.saveUploads(uploads);

    // Start upload immediately
    this.processUpload(id, options);

    return id;
  }

  // Process a single upload with retry logic
  private async processUpload(uploadId: string, options?: UploadOptions): Promise<void> {
    const uploads = this.getUploads();
    const uploadIndex = uploads.findIndex(u => u.id === uploadId);

    if (uploadIndex === -1) {
      console.warn(`Upload ${uploadId} not found`);
      return;
    }

    const upload = uploads[uploadIndex];
    upload.status = 'in_progress';
    this.saveUploads(uploads);

    try {
      // Import API function dynamically to avoid circular dependencies
      const { processPartImagesAsync } = await import('./api');

      const response = await processPartImagesAsync(
        upload.files,
        upload.partNumber,
        upload.viewNumbers,
        options?.format || "PNG",
        options?.whiteBackground ?? true,
        options?.compressionQuality || 85,
        options?.maxDimension || 2048,
        options?.addLabel ?? true,
        options?.labelPosition || "bottom-left"
      );

      // Success - mark as completed
      upload.status = 'completed';
      upload.jobId = response.job_id;
      upload.completedAt = Date.now();
      upload.lastError = undefined;

      console.log(`✅ Upload completed: ${upload.partNumber} (${uploadId})`);

    } catch (error: any) {
      console.error(`❌ Upload failed: ${upload.partNumber} (${uploadId})`, error);

      upload.lastError = error.response?.data?.detail || error.message || 'Upload failed';

      // Check if we should retry
      const isRetryable = this.isRetryableError(error);
      const canRetry = upload.retryCount < upload.maxRetries && isRetryable;

      if (canRetry) {
        upload.retryCount++;
        upload.status = 'pending';

        // Schedule retry with exponential backoff
        const delay = this.retryDelays[upload.retryCount - 1] || 15000;
        console.log(`🔄 Retrying upload in ${delay}ms: ${upload.partNumber} (attempt ${upload.retryCount}/${upload.maxRetries})`);

        setTimeout(() => {
          this.processUpload(uploadId, options);
        }, delay);

      } else {
        // Failed permanently
        upload.status = 'failed';
        console.log(`💥 Upload permanently failed: ${upload.partNumber} (${uploadId})`);
      }
    }

    this.saveUploads(uploads);
  }

  // Check if error is retryable (network issues) vs permanent (404, 409)
  private isRetryableError(error: any): boolean {
    const status = error.response?.status;
    const message = error.response?.data?.detail || error.message || '';

    // Multipart boundary/parsing errors are always retryable (transmission corruption)
    if (status === 400 && (
      message.includes('boundary') ||
      message.includes('multipart') ||
      message.includes('CR at end') ||
      message.includes('parsing')
    )) {
      console.log('🔄 Retrying multipart boundary error:', message);
      return true;
    }

    // Don't retry other 4xx client errors (part not found, duplicate, validation)
    if (status >= 400 && status < 500) {
      return false;
    }

    // Retry network errors, timeouts, server errors
    return true;
  }

  // Get upload status by ID
  getUploadStatus(uploadId: string): UploadAttempt | null {
    const uploads = this.getUploads();
    return uploads.find(u => u.id === uploadId) || null;
  }

  // Get all uploads with optional status filter
  getAllUploads(status?: UploadAttempt['status']): UploadAttempt[] {
    const uploads = this.getUploads();
    if (status) {
      return uploads.filter(u => u.status === status);
    }
    return uploads;
  }

  // Get pending/failed uploads count
  getPendingCount(): { pending: number; failed: number; inProgress: number } {
    const uploads = this.getUploads();
    return {
      pending: uploads.filter(u => u.status === 'pending').length,
      failed: uploads.filter(u => u.status === 'failed').length,
      inProgress: uploads.filter(u => u.status === 'in_progress').length
    };
  }

  // Manually retry a failed upload
  retryUpload(uploadId: string, files: File[], options?: UploadOptions): void {
    const uploads = this.getUploads();
    const upload = uploads.find(u => u.id === uploadId);

    if (!upload || upload.status === 'completed') {
      console.warn(`Cannot retry upload ${uploadId}: not found or already completed`);
      return;
    }

    // Reset retry state
    upload.retryCount = 0;
    upload.status = 'pending';
    upload.lastError = undefined;
    upload.files = files; // Update with fresh files

    this.saveUploads(uploads);
    this.processUpload(uploadId, options);
  }

  // Clear old completed uploads (older than 24 hours)
  cleanup(): void {
    const uploads = this.getUploads();
    const dayAgo = Date.now() - (24 * 60 * 60 * 1000);

    const filtered = uploads.filter(upload => {
      // Keep failed/pending uploads
      if (upload.status === 'failed' || upload.status === 'pending' || upload.status === 'in_progress') {
        return true;
      }

      // Keep recent completed uploads
      return (upload.completedAt || upload.timestamp) > dayAgo;
    });

    if (filtered.length !== uploads.length) {
      console.log(`🧹 Cleaned up ${uploads.length - filtered.length} old uploads`);
      this.saveUploads(filtered);
    }
  }

  // Clear all uploads (for testing/reset)
  clearAll(): void {
    localStorage.removeItem(this.storageKey);
  }
}

// Export singleton instance
export const uploadTracker = new UploadTracker();

// Auto-cleanup on load
uploadTracker.cleanup();