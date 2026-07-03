"use client";

import { useRef, useState } from "react";

import {
  BatchResultsData,
  batchResults,
  exportCsvUrl,
  exportJsonUrl,
  jobStatus,
  startBatch,
} from "@/lib/api";

// Batch results screen (design §5.8): run async batch, watch progress, per-field rates, export.
export default function BatchResults({ batchId }: { batchId: string }) {
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [state, setState] = useState<string>("");
  const [results, setResults] = useState<BatchResultsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  async function run() {
    setError(null);
    setResults(null);
    try {
      const { job_id } = await startBatch(batchId);
      setState("queued");
      timer.current = setInterval(async () => {
        try {
          const s = await jobStatus(job_id);
          setState(s.state);
          setProgress(s.progress);
          if (s.state === "done" || s.state === "failed") {
            if (timer.current) clearInterval(timer.current);
            if (s.state === "done") setResults(await batchResults(batchId));
            else setError(s.error || "batch failed");
          }
        } catch (e) {
          if (timer.current) clearInterval(timer.current);
          setError(String(e));
        }
      }, 500);
    } catch (e) {
      setError(String(e));
    }
  }

  const pct = progress && progress.total ? Math.round((progress.done / progress.total) * 100) : 0;

  return (
    <div style={{ marginTop: 16, borderTop: "1px solid #cbd5e1", paddingTop: 12 }}>
      <button onClick={run} disabled={state === "running" || state === "queued"}>
        Run batch
      </button>
      {state && (
        <div style={{ margin: "8px 0" }}>
          <div style={{ fontSize: 13, color: "#475569" }}>
            {state} — {progress?.done ?? 0}/{progress?.total ?? 0}
          </div>
          <div style={{ background: "#e2e8f0", borderRadius: 4, height: 8, width: 260 }}>
            <div style={{ background: "#4f46e5", height: 8, borderRadius: 4, width: `${pct}%` }} />
          </div>
        </div>
      )}
      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}
      {results && (
        <div>
          <h3>Per-field failure rate</h3>
          <table style={{ fontSize: 13, borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", color: "#475569" }}>
                <th>Field</th>
                <th>Failures</th>
                <th>In scope</th>
                <th>Rate</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(results.field_rates).map(([name, r]) => (
                <tr key={name} style={{ borderTop: "1px solid #eef2f7" }}>
                  <td>{name}</td>
                  <td>{r.failures}</td>
                  <td>{r.in_scope}</td>
                  <td style={{ color: r.failure_rate >= 0.3 ? "#b91c1c" : "#15803d" }}>
                    {(r.failure_rate * 100).toFixed(0)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ marginTop: 8 }}>
            <a href={exportCsvUrl(batchId)}>Export CSV</a> ·{" "}
            <a href={exportJsonUrl(batchId)}>Export JSON</a>
          </p>
        </div>
      )}
    </div>
  );
}
