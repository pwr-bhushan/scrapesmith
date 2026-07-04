"use client";

import { useState } from "react";

import { checkSelector, getConfig, saveConfig } from "@/lib/api";

// Advanced mode (design §5.8 / §8): raw JSON config editor + custom selector checker + custom DQ.
export default function AdvancedPanel({ batchId, index }: { batchId: string; index: number }) {
  const [open, setOpen] = useState(false);
  const [json, setJson] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [sel, setSel] = useState("");
  const [check, setCheck] = useState<{ count: number; values: string[] } | null>(null);

  async function load() {
    const cfg = await getConfig(batchId);
    setJson(JSON.stringify(cfg.fields, null, 2));
    setMsg(`Loaded v${cfg.version ?? "—"}`);
  }

  async function validateAndSave() {
    setError(null);
    setMsg(null);
    let fields: unknown;
    try {
      fields = JSON.parse(json);
    } catch (e) {
      setError(`Invalid JSON: ${e}`);
      return;
    }
    if (!Array.isArray(fields) || fields.some((f) => !f || !f.name || !f.selector)) {
      setError("Config must be an array of fields with at least {name, selector}.");
      return;
    }
    try {
      const r = await saveConfig(batchId, fields as never);
      setMsg(`Saved config v${r.version} (${r.field_count} fields)`);
    } catch (e) {
      setError(String(e));
    }
  }

  async function runCheck() {
    setError(null);
    try {
      setCheck(await checkSelector(batchId, index, sel));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div style={{ marginTop: 16, borderTop: "1px solid #cbd5e1", paddingTop: 12 }}>
      <button onClick={() => setOpen((o) => !o)}>{open ? "Hide" : "Advanced ⌄"}</button>
      {open && (
        <div style={{ marginTop: 8 }}>
          <h4>Custom selector check (file {index + 1})</h4>
          <input
            placeholder="css=... or xpath=..."
            value={sel}
            onChange={(e) => setSel(e.target.value)}
            style={{ width: "70%", padding: 6 }}
          />{" "}
          <button onClick={runCheck}>Check</button>
          {check && (
            <p style={{ fontSize: 13, color: check.count ? "#15803d" : "#b91c1c" }}>
              resolves to {check.count} — {check.values.slice(0, 3).join(", ")}
            </p>
          )}

          <h4 style={{ marginTop: 12 }}>Raw JSON config (fields[])</h4>
          <button onClick={load}>Load current</button>
          <textarea
            value={json}
            onChange={(e) => setJson(e.target.value)}
            rows={12}
            style={{ width: "100%", fontFamily: "monospace", fontSize: 12, marginTop: 6 }}
            placeholder='[{"name":"price","selector":"css=[data-price]","scope":"single","dq":{"required":true,"parses_as":"number"}}]'
          />
          <button onClick={validateAndSave}>Validate &amp; Save</button>
          {msg && <p style={{ color: "#15803d" }}>{msg}</p>}
          {error && <p style={{ color: "#b91c1c" }}>{error}</p>}
        </div>
      )}
    </div>
  );
}
