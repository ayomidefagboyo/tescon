/** API client for backend communication */
import axios from "axios";
import { PartInfo, ProcessPartResponse } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for large uploads
});


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
    part_number: partNumber,
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
