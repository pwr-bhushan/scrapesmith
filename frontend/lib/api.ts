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
  anchor?: { value: string; fingerprint?: unknown } | null;
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

export interface CanaryResult {
  file_index: number;
  filename: string;
  config_version: number;
  data: Record<string, unknown>;
  field_status: Record<string, string>;
  flags: Record<string, string[]>;
  anchor_ok: Record<string, boolean | null>;
}

export async function canary(batchId: string, index: number): Promise<CanaryResult> {
  const res = await fetch(`${API_BASE}/parse/canary`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ batch_id: batchId, index }),
  });
  if (!res.ok) throw new Error(`canary failed (${res.status}): ${await res.text()}`);
  return res.json();
}

// ---- Phase 5: async batch + export ----

export interface JobStatus {
  job_id: string;
  state: string;
  progress: { done: number; total: number; phase: string };
  error: string | null;
}

export async function startBatch(batchId: string): Promise<{ job_id: string; config_version: number }> {
  const res = await fetch(`${API_BASE}/parse/batch`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ batch_id: batchId }),
  });
  if (!res.ok) throw new Error(`startBatch failed (${res.status}): ${await res.text()}`);
  return res.json();
}

export async function jobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`jobStatus failed: ${res.status}`);
  return res.json();
}

export interface FieldRate {
  failures: number;
  in_scope: number;
  failure_rate: number;
}

export interface BatchResultsData {
  config_version: number;
  file_count: number;
  field_rates: Record<string, FieldRate>;
  flagged: { file: string; flagged_ratio: number }[];
  rows: { file: string; data: Record<string, unknown> }[];
}

export async function batchResults(batchId: string): Promise<BatchResultsData> {
  const res = await fetch(`${API_BASE}/batch/${batchId}/results`, { cache: "no-store" });
  if (!res.ok) throw new Error(`results failed: ${res.status}`);
  return res.json();
}

export function exportCsvUrl(batchId: string): string {
  return `${API_BASE}/batch/${batchId}/export.csv`;
}

export function exportJsonUrl(batchId: string): string {
  return `${API_BASE}/batch/${batchId}/export.json`;
}

// ---- Phase 6: heal ----

export interface HealProposal {
  selector: string;
  status: "healed" | "suspect" | "still_broken";
  value: string | null;
  anchor_ok: boolean | null;
  anchor?: string | null;
}

export interface HealCluster {
  hash: string;
  size: number;
  representative: string;
  model: string;
  proposals: Record<string, HealProposal>;
}

export interface HealProposeResult {
  triggered: boolean;
  failing?: string[];
  clusters?: HealCluster[];
  field_rates: Record<string, FieldRate>;
}

export async function healPropose(batchId: string): Promise<HealProposeResult> {
  const res = await fetch(`${API_BASE}/heal/propose`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ batch_id: batchId }),
  });
  if (!res.ok) throw new Error(`healPropose failed (${res.status}): ${await res.text()}`);
  return res.json();
}

export async function healAccept(
  batchId: string,
  accepted: Record<string, string>
): Promise<{ config_version_id: string; version: number; healed: string[] }> {
  const res = await fetch(`${API_BASE}/heal/accept`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ batch_id: batchId, accepted }),
  });
  if (!res.ok) throw new Error(`healAccept failed (${res.status}): ${await res.text()}`);
  return res.json();
}

// ---- Phase 7: versions ----

export interface VersionInfo {
  id: string;
  version: number;
  created_by: string | null;
  parent_version: number | null;
  field_count: number;
}

export async function listVersions(domainId: string): Promise<VersionInfo[]> {
  const res = await fetch(`${API_BASE}/domains/${domainId}/versions`, { cache: "no-store" });
  if (!res.ok) throw new Error(`listVersions failed: ${res.status}`);
  return (await res.json()).versions;
}

export interface VersionDiff {
  added: string[];
  removed: string[];
  changed: Record<string, Record<string, [unknown, unknown]>>;
}

export async function diffVersions(domainId: string, a: number, b: number): Promise<VersionDiff> {
  const res = await fetch(`${API_BASE}/domains/${domainId}/diff?a=${a}&b=${b}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`diff failed: ${res.status}`);
  return (await res.json()).diff;
}

export async function pinBatch(
  batchId: string,
  version: number
): Promise<{ pinned_version: number }> {
  const res = await fetch(`${API_BASE}/batch/${batchId}/pin`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ version }),
  });
  if (!res.ok) throw new Error(`pin failed: ${res.status}`);
  return res.json();
}
