"use client";

import { useState } from "react";

import { Descriptor, validatePick, ValidateResult } from "@/lib/api";

export interface PendingPick {
  descriptor: Descriptor;
  text: string;
  listParent: { selector: string; count: number } | null;
}

// Click popover (design §5.3, Phase 2 subset: no inference/✨ yet).
export default function PickPopover({
  batchId,
  index,
  pick,
  onConfirm,
  onCancel,
}: {
  batchId: string;
  index: number;
  pick: PendingPick;
  onConfirm: (field: {
    name: string;
    selector: string;
    scope: string;
    list_parent_selector: string | null;
  }) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"single" | "list">("single");
  const [result, setResult] = useState<ValidateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function validate() {
    setBusy(true);
    setError(null);
    try {
      const r = await validatePick({
        batch_id: batchId,
        index,
        descriptor: pick.descriptor,
        scope,
        list_parent_selector: scope === "list" ? pick.listParent?.selector : null,
      });
      setResult(r);
      if (!r.resolves) setError("Selector did not uniquely resolve — try the other scope.");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function confirm() {
    if (!result?.resolves || !result.selector || !name.trim()) return;
    onConfirm({
      name: name.trim(),
      selector: result.selector,
      scope,
      list_parent_selector: result.list_parent_selector,
    });
  }

  return (
    <div style={card}>
      <div style={{ fontSize: 13, color: "#475569" }}>Value: “{pick.text || "(empty)"}”</div>
      <label style={{ display: "block", margin: "8px 0" }}>
        <input
          type="radio"
          checked={scope === "single"}
          onChange={() => setScope("single")}
        />{" "}
        Just this one
      </label>
      {pick.listParent && (
        <label style={{ display: "block", marginBottom: 8 }}>
          <input type="radio" checked={scope === "list"} onChange={() => setScope("list")} /> All{" "}
          {pick.listParent.count} similar items
        </label>
      )}
      <input
        placeholder="Field name (e.g. price)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ width: "100%", padding: 6, marginBottom: 8 }}
      />
      {result && result.resolves && (
        <div style={{ color: "#15803d", fontSize: 13 }}>
          ✓ resolves to {result.count} — {result.values.slice(0, 3).join(", ")}
        </div>
      )}
      {error && <div style={{ color: "#b91c1c", fontSize: 13 }}>{error}</div>}
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button onClick={validate} disabled={busy}>
          {busy ? "Checking…" : "Check"}
        </button>
        <button onClick={confirm} disabled={!result?.resolves || !name.trim()}>
          Confirm
        </button>
        <button onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

const card: React.CSSProperties = {
  border: "1px solid #cbd5e1",
  borderRadius: 8,
  padding: 12,
  background: "white",
  boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
};
