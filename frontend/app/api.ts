const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let authToken: string | null = null;
let vaultToken: string | null = null;

export const setAuthToken = (token: string | null) => {
  authToken = token;
};

export const setVaultToken = (token: string | null) => {
  vaultToken = token;
};

export const getAuthToken = () => authToken;

const getHeaders = (isFormData = false) => {
  const headers: HeadersInit = {};
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  if (vaultToken) {
    headers["X-Vault-Token"] = vaultToken;
  }
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
};

export interface AuthResponse {
  access_token: string;
  token_type: string;
  mode: "real" | "panic";
}

export interface ImageInfo {
  id: string;
  filename: string;
  original_name: string;
  resolution: string;
  file_size: string;
  capacity: string;
  has_hidden_data: boolean;
  hidden_file_name: string | null;
  hidden_file_size: string | null;
  created_at: string;
  thumbnail_url: string;
  full_url: string;
}

export interface GalleryResponse {
  success: boolean;
  total: number;
  images: ImageInfo[];
}

export interface UploadResponse {
  success: boolean;
  message: string;
  image: ImageInfo;
}

export interface ExtractResponse {
  success: boolean;
  message: string;
  extracted_file: string;
  file_size: string;
  download_url: string;
}

export interface CapacityResponse {
  success: boolean;
  image_id: string;
  resolution: string;
  total_pixels: number;
  max_capacity: string;
  max_capacity_bytes: number;
}

// ─── Auth ───
export async function login(password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/vault/login`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ password }),
  });
  if (!res.ok) {
    throw new Error("Invalid password");
  }
  return res.json();
}

// ─── Gallery ───
export async function fetchGallery(filter?: string): Promise<GalleryResponse> {
  const url = new URL(`${API_BASE}/api/gallery`);
  if (filter) url.searchParams.set("filter", filter);
  const res = await fetch(url.toString(), {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error(`Gallery fetch failed: ${res.status}`);
  return res.json();
}

// ─── Upload Secret ───
export async function uploadSecret(
  secretFile: File,
  password: string,
  carrierImage?: File,
  carrierDescription?: string
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("secret_file", secretFile);
  form.append("password", password);
  if (carrierImage) form.append("carrier_image", carrierImage);
  if (carrierDescription) form.append("carrier_description", carrierDescription);

  const res = await fetch(`${API_BASE}/api/upload-secret`, {
    method: "POST",
    headers: getHeaders(true),
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

// ─── Extract Secret ───
export async function extractSecret(
  imageId: string,
  password: string
): Promise<ExtractResponse> {
  const form = new FormData();
  form.append("image_id", imageId);
  form.append("password", password);

  const res = await fetch(`${API_BASE}/api/extract-secret`, {
    method: "POST",
    headers: getHeaders(true),
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Extraction failed" }));
    throw new Error(err.detail || "Extraction failed");
  }
  return res.json();
}

// ─── Download Extracted File ───
export function getDownloadUrl(downloadPath: string): string {
  const url = new URL(`${API_BASE}${downloadPath}`);
  if (vaultToken) url.searchParams.set("token", vaultToken);
  return url.toString();
}

// ─── Image URL ───
export function getImageUrl(imageId: string): string {
  const url = new URL(`${API_BASE}/api/images/${imageId}`);
  if (vaultToken) url.searchParams.set("token", vaultToken);
  return url.toString();
}

// ─── Delete Image ───
export async function deleteImage(imageId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/images/${imageId}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Delete failed");
}

// ─── Generate Carrier ───
export async function generateCarrier(description: string): Promise<UploadResponse> {
  const form = new FormData();
  form.append("description", description);

  const res = await fetch(`${API_BASE}/api/generate-carrier`, {
    method: "POST",
    headers: getHeaders(true),
    body: form,
  });

  if (!res.ok) throw new Error("Carrier generation failed");
  return res.json();
}

// ─── Upload Carrier (Standard Upload) ───
export async function uploadCarrier(image: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("image", image);

  const res = await fetch(`${API_BASE}/api/upload-carrier`, {
    method: "POST",
    headers: getHeaders(true),
    body: form,
  });

  if (!res.ok) throw new Error("Carrier upload failed");
  return res.json();
}

// ─── Seed Decoy ───
export async function seedDecoyPhotos(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/seed-decoy`, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Decoy seed failed");
}

// ─── Vault Setup & Share ───
export async function setupVault(password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/vault/setup`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ password }),
  });
  if (!res.ok) throw new Error("Vault setup failed");
  return res.json();
}

export async function checkVaultStatus(): Promise<{ has_password: boolean }> {
  const res = await fetch(`${API_BASE}/api/vault/status`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Status check failed");
  return res.json();
}
