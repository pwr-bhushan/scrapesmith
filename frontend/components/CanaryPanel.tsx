"use client";

import { CanaryResult } from "@/lib/api";

// Canary result panel (design §5.5): one file parsed, per-field value + DQ status + anchor match.
export default function CanaryPanel({ result }: { result: CanaryResult }) {
  const names = Object.keys(result.field_status);
  return (
    <div style={{ marginTop: 12, border: "1px solid #cbd5e1", borderRadius: 6, padding: 12 }}>
      <strong>
        Canary — {result.filename} (config v{result.config_version})
      </strong>
      <table style={{ width: "100%", fontSize: 13, marginTop: 8, borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", color: "#475569" }}>
            <th>Field</th>
            <th>Value</th>
            <th>DQ</th>
            <th>Anchor</th>
          </tr>
        </thead>
        <tbody>
          {names.map((n) => {
            const status = result.field_status[n];
            const value = result.data[n];
            const anchor = result.anchor_ok[n];
            return (
              <tr key={n} style={{ borderTop: "1px solid #eef2f7" }}>
                <td>{n}</td>
                <td>{Array.isArray(value) ? `[${value.length}] ${value.slice(0, 3).join(", ")}` : String(value ?? "—")}</td>
                <td style={{ color: status === "ok" ? "#15803d" : "#b91c1c" }}>{status}</td>
                <td>{anchor === null ? "—" : anchor ? "✓" : "✗ diverged"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
