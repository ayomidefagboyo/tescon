/** Type definitions for the application */

export interface FileWithPreview extends File {
  preview?: string;
  renamed?: string;  // New name if user renames
}

export interface PartInfo {
  part_number: string;
  description: string;
  location: string;
  item_note: string;
}

export interface ProcessPartResponse {
  success: boolean;
  part_number: string;
  description: string;
  location: string;
  item_note?: string;
  files_saved: number;
  saved_paths: Array<{
    filename: string;
    url: string;
  }>;
  download_url?: string;
  message: string;
}

export interface JobResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  total_images: number;
  processed_count: number;
  failed_count: number;
  failed_images?: string[];
  error_messages?: string[];
  parts_organized?: number;
}
