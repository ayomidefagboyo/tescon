/** API client for backend communication */
import axios, { AxiosProgressEvent } from "axios";
import { JobResponse, JobStatusResponse, FilenameValidationResponse, ExportValidationResponse } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for large uploads
});

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

/**
 * Validate filenames before upload
 */
export async function validateFilenames(files: File[]): Promise<FilenameValidationResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await api.post<FilenameValidationResponse>("/validate/filenames", formData);
  return response.data;
}

/**
 * Process a single image synchronously
 */
export async function processSingleImage(
  file: File,
  format: "PNG" | "JPEG" | "JPG" = "PNG",
  whiteBackground: boolean = true,
  onProgress?: (progress: UploadProgress) => void
): Promise<Blob> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(
    `/process/single?format=${format}&white_background=${whiteBackground}`,
    formData,
    {
      responseType: "blob",
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (onProgress && progressEvent.total) {
          onProgress({
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage: Math.round((progressEvent.loaded / progressEvent.total) * 100),
          });
        }
      },
    }
  );

  return response.data;
}

/**
 * Process multiple images asynchronously (bulk)
 */
export async function processBulkImages(
  files: File[],
  format: "PNG" | "JPEG" | "JPG" = "PNG",
  whiteBackground: boolean = true,
  compressionQuality: number = 85,
  maxDimension: number = 2048
): Promise<JobResponse> {
  const formData = new FormData();
  
  // Check if single ZIP file
  if (files.length === 1 && files[0].name.toLowerCase().endsWith(".zip")) {
    formData.append("files", files[0]);
  } else {
    // Multiple image files
    files.forEach((file) => {
      formData.append("files", file);
    });
  }

  const response = await api.post<JobResponse>(
    `/process/bulk?format=${format}&white_background=${whiteBackground}&compression_quality=${compressionQuality}&max_dimension=${maxDimension}`,
    formData
  );

  return response.data;
}

/**
 * Get job status
 */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await api.get<JobStatusResponse>(`/jobs/${jobId}`);
  return response.data;
}

/**
 * Download job results as ZIP
 */
export async function downloadJobResults(jobId: string): Promise<Blob> {
  const response = await api.get(`/jobs/${jobId}/download`, {
    responseType: "blob",
  });
  return response.data;
}

/**
 * Retry failed images from a job
 */
export async function retryFailedImages(
  jobId: string,
  format: "PNG" | "JPEG" | "JPG" = "PNG",
  whiteBackground: boolean = true
): Promise<JobResponse> {
  const response = await api.post<JobResponse>(
    `/jobs/${jobId}/retry?format=${format}&white_background=${whiteBackground}`
  );
  return response.data;
}

/**
 * Validate export before download
 */
export async function validateExport(jobId: string): Promise<ExportValidationResponse> {
  const response = await api.get<ExportValidationResponse>(`/jobs/${jobId}/validate-export`);
  return response.data;
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string; gpu_available: boolean; model_loaded: boolean }> {
  // Health endpoint is at root level, not /api/health
  const response = await axios.get("http://localhost:8001/health");
  return response.data;
}
