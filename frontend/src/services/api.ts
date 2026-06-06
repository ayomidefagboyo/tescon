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

interface DirectUploadTarget {
  filename: string;
  content_type: string;
  r2_key: string;
  upload_url: string;
  headers: Record<string, string>;
}

interface DirectUploadInitResponse {
  job_id: string;
  status: string;
  symbol_number: string;
  upload_targets: DirectUploadTarget[];
  message: string;
}

/**
 * Queue images using browser-to-R2 direct upload.
 *
 * Render validates/sorts metadata, but the image bytes go straight to R2.
 */
export async function processPartImagesDirect(
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

  const initResponse = await api.post<DirectUploadInitResponse>(
    `/process/part/direct/initiate?${params.toString()}`,
    {
      files: files.map((file) => ({
        filename: file.name,
        content_type: file.type || "application/octet-stream",
        size: file.size,
      })),
    },
    { timeout: 30000 }
  );

  const { job_id, upload_targets } = initResponse.data;
  if (upload_targets.length !== files.length) {
    throw new Error("Direct upload target count did not match selected files");
  }

  try {
    await Promise.all(upload_targets.map((target, index) => {
      const file = files[index];
      return axios.put(target.upload_url, file, {
        headers: target.headers,
        timeout: 300000,
      });
    }));
  } catch (error) {
    await api.post(
      "/process/part/direct/abort",
      {
        job_id,
        symbol_number: partNumber,
        files: upload_targets.map((target) => ({
          filename: target.filename,
          r2_key: target.r2_key,
          content_type: target.content_type,
        })),
      },
      { timeout: 30000 }
    ).catch((cleanupError) => {
      console.warn("Failed to clean up partial direct upload:", cleanupError);
    });

    const fallbackError = new Error("Direct R2 upload failed") as Error & {
      allowLegacyFallback?: boolean;
      originalError?: unknown;
    };
    fallbackError.allowLegacyFallback = true;
    fallbackError.originalError = error;
    throw fallbackError;
  }

  const finalizeResponse = await api.post<JobResponse>(
    "/process/part/direct/finalize",
    {
      job_id,
      symbol_number: partNumber,
      files: upload_targets.map((target) => ({
        filename: target.filename,
        r2_key: target.r2_key,
        content_type: target.content_type,
      })),
    },
    { timeout: 30000 }
  );

  return finalizeResponse.data;
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

export interface FullReportResponse {
  success: boolean;
  filename: string;
  url: string;
  total_tracked: number;
  completed: number;
  queued: number;
  failed: number;
}

export async function exportFullReport(date?: string, status?: string): Promise<FullReportResponse> {
  const params = new URLSearchParams();
  if (date) params.append('date', date);
  if (status) params.append('status', status);
  // mode=link is the default — returns JSON with a permanent report URL
  const response = await api.get<FullReportResponse>(`/tracker/export-full-report?${params.toString()}`, {
    timeout: 120000, // 2 min timeout — report may be large
  });

  // The backend returns a relative path like /api/reports/filename.xlsx.
  // Resolve it to a full URL so window.open and link sharing work correctly.
  const data = response.data;
  if (data.url && data.url.startsWith('/')) {
    // Use the same origin as the API base
    const apiBase = import.meta.env.VITE_API_URL;
    if (apiBase && !apiBase.startsWith('/')) {
      // Absolute API URL (e.g. https://my-backend.render.com/api)
      // Strip /api suffix to get the origin, then append the path
      const origin = apiBase.replace(/\/api\/?$/, '');
      data.url = `${origin}${data.url}`;
    } else {
      // Same-origin deployment — relative path works as-is, but make it absolute
      data.url = `${window.location.origin}${data.url}`;
    }
  }

  return data;
}

export async function syncTrackerFromR2(): Promise<any> {
  const response = await api.post('/tracker/sync-from-r2', {}, { timeout: 120000 }); // 2 minute timeout for R2 sync
  return response.data;
}
