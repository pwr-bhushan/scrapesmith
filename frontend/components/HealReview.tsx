"use client";

import { useState } from "react";

import { HealProposeResult, healAccept, healPropose } from "@/lib/api";

// Drift + value-first heal review (design §5.6/§5.7): show proposed value vs anchor, suspect flag,
// accept per field. Values first, selectors are secondary.
export default function HealReview({ batchId }: { batchId: string }) {
  const [result, setResult] = useState<HealProposeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [accepted, setAccepted] = useState<Record<string, string>>({});
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  async function check() {
    setError(null);
    setSavedMsg(null);
    try {
      const r = await healPropose(batchId);
      setResult(r);
      // pre-select healed fields
      const pre: Record<string, string> = {};
      r.clusters?.forEach((cl) =>
        Object.entries(cl.proposals).forEach(([name, p]) => {
          if (p.status === "healed") pre[name] = p.selector;
        })
      );
      setAccepted(pre);
    } catch (e) {
      setError(String(e));
    }
  }

  async function accept() {
    try {
      const r = await healAccept(batchId, accepted);
      setSavedMsg(`Applied heal → config v${r.version} (${r.healed.join(", ")})`);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div style={{ marginTop: 16, borderTop: "1px solid #cbd5e1", paddingTop: 12 }}>
      <button onClick={check}>Check for drift</button>
      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}
      {result && !result.triggered && (
        <p style={{ color: "#15803d" }}>No drift — all fields under threshold.</p>
      )}
      {result?.triggered && (
        <div>
          <p style={{ color: "#b91c1c" }}>Drift detected on: {result.failing?.join(", ")}</p>
          {result.clusters?.map((cl) => (
            <div key={cl.hash} style={{ border: "1px solid #e2e8f0", borderRadius: 6, padding: 10, marginBottom: 8 }}>
              <div style={{ fontSize: 13, color: "#475569" }}>
                Cluster {cl.hash.slice(0, 8)} · {cl.size} file(s) · model: {cl.model}
              </div>
              {cl.model === "unavailable" ? (
                <p style={{ color: "#a16207" }}>
                  ✨ No heal model configured (set ANTHROPIC_API_KEY or OLLAMA_HOST).
                </p>
              ) : (
                <table style={{ width: "100%", fontSize: 13, marginTop: 6 }}>
                  <thead>
                    <tr style={{ textAlign: "left", color: "#475569" }}>
                      <th>Accept</th>
                      <th>Field</th>
                      <th>Proposed value</th>
                      <th>Anchor</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(cl.proposals).map(([name, p]) => (
                      <tr key={name}>
                        <td>
                          <input
                            type="checkbox"
                            disabled={p.status === "still_broken"}
                            checked={accepted[name] === p.selector}
                            onChange={(e) =>
                              setAccepted((prev) => {
                                const next = { ...prev };
                                if (e.target.checked) next[name] = p.selector;
                                else delete next[name];
                                return next;
                              })
                            }
                          />
                        </td>
                        <td>{name}</td>
                        <td>{p.value ?? "—"}</td>
                        <td>{p.anchor ?? "—"}</td>
                        <td
                          style={{
                            color:
                              p.status === "healed"
                                ? "#15803d"
                                : p.status === "suspect"
                                ? "#a16207"
                                : "#b91c1c",
                          }}
                        >
                          {p.status}
                          {p.anchor_ok === false && " · diverged"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ))}
          <button onClick={accept} disabled={Object.keys(accepted).length === 0}>
            Accept selected
          </button>
          {savedMsg && <p style={{ color: "#15803d" }}>{savedMsg}</p>}
        </div>
      )}
    </div>
  );
}
