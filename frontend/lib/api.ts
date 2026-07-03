// Shared typed API client.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface Health {
  status: string;
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`health failed: ${res.status}`);
  return res.json();
}

export interface UploadResult {
  batch_id: string;
  domain_id: string;
  file_count: number;
  files: { index: number; filename: string }[];
}

export async function uploadBatch(form: FormData): Promise<UploadResult> {
  const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`upload failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export interface BatchFile {
  index: number;
  filename: string;
  dom_skeleton_hash: string | null;
}

export interface BatchInfo {
  batch_id: string;
  domain_id: string;
  status: string | null;
  file_count: number | null;
  files: BatchFile[];
}

export async function getBatch(id: string): Promise<BatchInfo> {
  const res = await fetch(`${API_BASE}/batch/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`getBatch failed: ${res.status}`);
  return res.json();
}

export function renderUrl(batchId: string, index: number): string {
  return `${API_BASE}/batch/${batchId}/file/${index}/render`;
}
