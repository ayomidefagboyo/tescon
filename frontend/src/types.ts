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
  message: string;
}
