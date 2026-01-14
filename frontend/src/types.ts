/** Type definitions for the application */

export enum JobStatus {
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  total_images: number;
  processed_count: number;
  failed_count: number;
  failed_images?: string[];
  error_messages?: string[];
}

export interface FileWithPreview extends File {
  preview?: string;
}

