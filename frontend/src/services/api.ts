/** API client for backend communication */
import axios from "axios";
import { PartInfo, ProcessPartResponse, JobResponse, JobStatusResponse } from "../types";

// Re-export types for convenience
export type { PartInfo, ProcessPartResponse, JobResponse, JobStatusResponse } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for large uploads
});

const TRACKER_TIMEOUT_MS = 30000;
const TRACKER_RETRY_DELAY_MS = 1500;


/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string; gpu_available: boolean; model_loaded: boolean }> {
  // Health endpoint is at root level, not /api/health
  const healthUrl = import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL.replace('/api', '')}/health`
    : "/health";
  const response = await axios.get(healthUrl);
  return response.data;
}

/**
 * Get part information from Google Sheets
 */
export async function getPartInfo(partNumber: string): Promise<PartInfo> {
  const response = await api.get<PartInfo>(`/parts/${encodeURIComponent(partNumber)}`);
  return response.data;
}

/**
 * Search parts by query (for autocomplete)
 */
export async function searchParts(query: string, limit: number = 10): Promise<PartInfo[]> {
  const response = await api.get<PartInfo[]>(`/parts/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  return response.data;
}

/**
 * Process images for a part (simplified workflow)
 */
export async function processPartImages(
  files: File[],
  partNumber: string,
  viewNumbers?: number[],
  format: "PNG" | "JPEG" | "JPG" = "PNG",
  whiteBackground: boolean = true,
  compressionQuality: number = 85,
  maxDimension: number = 2048,
  addLabel: boolean = true,
  labelPosition: "bottom-left" | "bottom-right" | "top-left" | "top-right" | "bottom-center" = "bottom-left"
): Promise<ProcessPartResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  const params = new URLSearchParams({
    symbol_number: partNumber,
    format,
    white_background: whiteBackground.toString(),
    compression_quality: compressionQuality.toString(),
    max_dimension: maxDimension.toString(),
    add_label: addLabel.toString(),
    label_position: labelPosition,
  });

  if (viewNumbers && viewNumbers.length > 0) {
    params.append("view_numbers", viewNumbers.join(","));
  }

  const response = await api.post<ProcessPartResponse>(
    `/process/part?${params.toString()}`,
    formData
  );

  return response.data;
}

/**
 * Queue images for async background processing
 */
export async function processPartImagesAsync(
  files: File[],
  partNumber: string,
  viewNumbers?: number[],
  format: "PNG" | "JPEG" | "JPG" = "PNG",
  whiteBackground: boolean = true,
  compressionQuality: number = 85,
  maxDimension: number = 2048,
  addLabel: boolean = true,
  labelPosition: "bottom-left" | "bottom-right" | "top-left" | "top-right" | "bottom-center" = "bottom-left"
): Promise<JobResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  const params = new URLSearchParams({
    symbol_number: partNumber,
    format,
    white_background: whiteBackground.toString(),
    compression_quality: compressionQuality.toString(),
    max_dimension: maxDimension.toString(),
    add_label: addLabel.toString(),
    label_position: labelPosition,
  });

  if (viewNumbers && viewNumbers.length > 0) {
    params.append("view_numbers", viewNumbers.join(","));
  }

  const response = await api.post<JobResponse>(
    `/process/part/async?${params.toString()}`,
    formData,
    {
      timeout: 300000, // 5 minute timeout for uploads
    }
  );

  return response.data;
}

/**
 * Check job status
 */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await api.get<JobStatusResponse>(`/jobs/${jobId}/status`);
  return response.data;
}

/**
 * Tracker API functions
 */
export function describeApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const responseData = error.response?.data;
    const detail =
      typeof responseData === 'string'
        ? responseData
        : responseData?.detail || responseData?.message;

    if (status && detail) {
      return `HTTP ${status}: ${detail}`;
    }

    if (status) {
      return `HTTP ${status}`;
    }

    if (error.code === 'ECONNABORTED') {
      return 'Request timed out while waiting for the backend';
    }

    if (error.message) {
      return error.message;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Unknown network error';
}

const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

export async function getTrackerProgress(): Promise<any> {
  for (let attempt = 1; attempt <= 2; attempt++) {
    try {
      const response = await api.get('/tracker/progress', {
        timeout: TRACKER_TIMEOUT_MS,
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        },
        params: {
          '_t': Date.now(),
          'include_part_stats': false
        }
      });
      return response.data;
    } catch (error) {
      const isRetryable = axios.isAxiosError(error) && (!error.response || error.code === 'ECONNABORTED');
      const willRetry = attempt === 1 && isRetryable;

      console.error('Tracker progress request failed:', {
        attempt,
        message: describeApiError(error),
        code: axios.isAxiosError(error) ? error.code : undefined,
        status: axios.isAxiosError(error) ? error.response?.status : undefined,
        willRetry
      });

      if (!willRetry) {
        throw error;
      }

      await wait(TRACKER_RETRY_DELAY_MS);
    }
  }

  throw new Error('Tracker progress request failed after retry');
}

export async function getProcessedParts(): Promise<any> {
  const response = await api.get('/tracker/parts/processed', {
    timeout: 10000, // 10s timeout
    headers: {
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache'
    },
    params: {
      '_t': Date.now() // Cache busting
    }
  });
  return response.data;
}

export async function getFailedParts(): Promise<any> {
  const response = await api.get('/tracker/parts/failed', { timeout: 10000 }); // 10s timeout
  return response.data;
}

export async function getRemainingParts(): Promise<any> {
  const response = await api.get('/tracker/parts/remaining', { timeout: 10000 }); // 10s timeout
  return response.data;
}

export async function getQueuedParts(): Promise<any> {
  const response = await api.get('/tracker/parts/queued', { timeout: 10000 }); // 10s timeout
  return response.data;
}

export async function resetPartStatus(partNumber: string): Promise<void> {
  await api.post(`/tracker/parts/${partNumber}/reset`);
}

export async function getDailyStats(date?: string, status?: string): Promise<any> {
  const params = new URLSearchParams();
  if (date) params.append('date', date);
  if (status) params.append('status', status);
  const response = await api.get(`/tracker/daily-stats?${params.toString()}`);
  return response.data;
}

export async function exportDailyStatsExcel(date?: string, status?: string): Promise<Blob> {
  const params = new URLSearchParams();
  if (date) params.append('date', date);
  if (status) params.append('status', status);
  const response = await api.get(`/tracker/export-daily-stats?${params.toString()}`, {
    responseType: 'blob'
  });
  return response.data;
}

export async function syncTrackerFromR2(): Promise<any> {
  const response = await api.post('/tracker/sync-from-r2', {}, { timeout: 120000 }); // 2 minute timeout for R2 sync
  return response.data;
}
