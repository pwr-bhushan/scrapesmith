// Shared typed API client. Phase 0.5: just /health.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface Health {
  status: string;
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`health failed: ${res.status}`);
  return res.json();
}
