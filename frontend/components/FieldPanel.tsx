"use client";

import { useState } from "react";

import { ConfigFieldInput, saveConfig } from "@/lib/api";

// Right-hand field panel (§5.2): confirmed fields + Save config v1.
export default function FieldPanel({
  batchId,
  fields,
  onRemove,
}: {
  batchId: string;
  fields: ConfigFieldInput[];
  onRemove: (i: number) => void;
}) {
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setError(null);
    try {
      const r = await saveConfig(batchId, fields);
      setSaved(`Saved config v${r.version} (${r.field_count} fields)`);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div style={{ minWidth: 220 }}>
      <h3>Fields</h3>
      {fields.length === 0 && <p style={{ color: "#94a3b8" }}>Click an element to add a field.</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {fields.map((f, i) => (
          <li key={i} style={{ marginBottom: 8 }}>
            <strong>{f.name}</strong> <em style={{ color: "#64748b" }}>({f.scope})</em>
            <br />
            <code style={{ fontSize: 12 }}>{f.selector}</code>{" "}
            <button onClick={() => onRemove(i)} style={{ fontSize: 11 }}>
              ✕
            </button>
          </li>
        ))}
      </ul>
      <button onClick={save} disabled={fields.length === 0}>
        Save config
      </button>
      {saved && <p style={{ color: "#15803d" }}>{saved}</p>}
      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}
    </div>
  );
}
