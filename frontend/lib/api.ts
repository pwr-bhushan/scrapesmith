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

// ---- Phase 2: pick + config ----

export interface Descriptor {
  tag: string;
  id?: string;
  classes?: string[];
  data?: Record<string, string>;
  itemprop?: string;
  role?: string;
  landmark?: string | null;
  nth_of_type?: number;
}

export interface ValidateResult {
  resolves: boolean;
  selector: string | null;
  count: number;
  values: string[];
  scope: string;
  list_parent_selector: string | null;
}

export async function validatePick(body: {
  batch_id: string;
  index: number;
  descriptor: Descriptor;
  scope: string;
  list_parent_selector?: string | null;
}): Promise<ValidateResult> {
  const res = await fetch(`${API_BASE}/pick/validate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`validate failed: ${res.status}`);
  return res.json();
}

export interface InferResult {
  type: string | null;
  confidence: number;
  source: string;
  dq: Record<string, unknown>;
}

export async function infer(body: {
  text?: string;
  itemprop?: string;
  data?: Record<string, string>;
  label?: string;
  use_llm?: boolean;
}): Promise<InferResult> {
  const res = await fetch(`${API_BASE}/infer`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`infer failed: ${res.status}`);
  return res.json();
}

export async function getPresets(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/presets`, { cache: "no-store" });
  if (!res.ok) throw new Error(`presets failed: ${res.status}`);
  return (await res.json()).types;
}

export interface ConfigFieldInput {
  name: string;
  selector: string;
  scope: string;
  list_parent_selector?: string | null;
  type?: string | null;
  dq?: Record<string, unknown> | null;
}

export async function saveConfig(
  batchId: string,
  fields: ConfigFieldInput[]
): Promise<{ config_version_id: string; version: number; field_count: number }> {
  const res = await fetch(`${API_BASE}/batch/${batchId}/config`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!res.ok) throw new Error(`saveConfig failed: ${res.status}`);
  return res.json();
}
