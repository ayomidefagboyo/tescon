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
  validation_results?: FilenameValidationResponse;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  total_images: number;
  processed_count: number;
  failed_count: number;
  failed_images?: string[];
  error_messages?: string[];
  parts_organized?: number;
}

export interface FileWithPreview extends File {
  preview?: string;
  renamed?: string;  // New name if user renames
}

export interface ParsedFilenameInfo {
  part_number: string;
  view_number: string;
  location: string;
  original_filename: string;
  is_valid: boolean;
  error_message?: string;
}

export interface FilenameValidationResponse {
  total_files: number;
  valid_files: number;
  invalid_files: number;
  unique_parts: number;
  invalid_details: Array<{
    filename: string;
    error: string;
  }>;
  parts_summary: Array<{
    part_number: string;
    view_count: number;
    views: string[];
    locations: string[];
  }>;
}

export interface ExportValidationResponse {
  is_valid: boolean;
  total_parts: number;
  total_images: number;
  missing_views: Array<{
    part_number: string;
    expected_views: number[];
    actual_views: number[];
    missing_views: string[];
  }>;
  corrupted_images: string[];
  warnings: string[];
}

export interface CompressionSettings {
  quality: number;
  max_dimension: number;
  preset?: string;
}
