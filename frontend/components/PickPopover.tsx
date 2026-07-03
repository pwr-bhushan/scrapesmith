"use client";

import { useEffect, useState } from "react";

import {
  Descriptor,
  getPresets,
  infer,
  InferResult,
  validatePick,
  ValidateResult,
} from "@/lib/api";

export interface PendingPick {
  descriptor: Descriptor;
  text: string;
  listParent: { selector: string; count: number } | null;
}

// Click popover (design §5.3): inferred type + confidence, Change dropdown, ✨ opt-in LLM, scope, name.
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
    type: string | null;
    dq: Record<string, unknown> | null;
  }) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"single" | "list">("single");
  const [result, setResult] = useState<ValidateResult | null>(null);
  const [inferred, setInferred] = useState<InferResult | null>(null);
  const [presets, setPresets] = useState<string[]>([]);
  const [chosenType, setChosenType] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getPresets().then(setPresets).catch(() => {});
    infer({
      text: pick.text,
      itemprop: pick.descriptor.itemprop,
      data: pick.descriptor.data,
    })
      .then((r) => {
        setInferred(r);
        if (r.type) {
          setChosenType(r.type);
          if (!name) setName(r.type);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function askAI() {
    setBusy(true);
    try {
      const r = await infer({ text: pick.text, label: name, use_llm: true });
      setInferred(r);
      if (r.type) setChosenType(r.type);
    } finally {
      setBusy(false);
    }
  }

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
      type: chosenType || inferred?.type || null,
      dq: chosenType === inferred?.type ? inferred?.dq ?? null : null,
    });
  }

  const confPct = inferred ? Math.round(inferred.confidence * 100) : 0;

  return (
    <div style={card}>
      <div style={{ fontSize: 13, color: "#475569" }}>
        Looks like:{" "}
        <strong>{inferred?.type ? inferred.type.toUpperCase() : "—"}</strong>
        {inferred?.type ? ` (${confPct}%)` : " couldn't auto-detect"}
        {inferred?.source === "llm_unavailable" && " · ✨ needs ANTHROPIC_API_KEY"}
      </div>
      <div style={{ fontSize: 13, color: "#475569", margin: "4px 0" }}>
        Value: “{pick.text || "(empty)"}”
      </div>

      <label style={{ display: "block", margin: "6px 0" }}>
        Type:{" "}
        <select value={chosenType} onChange={(e) => setChosenType(e.target.value)}>
          <option value="">(none)</option>
          {presets.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>{" "}
        <button onClick={askAI} disabled={busy} title="Ask AI (opt-in)">
          ✨
        </button>
      </label>

      <label style={{ display: "block" }}>
        <input type="radio" checked={scope === "single"} onChange={() => setScope("single")} /> Just
        this one
      </label>
      {pick.listParent && (
        <label style={{ display: "block" }}>
          <input type="radio" checked={scope === "list"} onChange={() => setScope("list")} /> All{" "}
          {pick.listParent.count} similar items
        </label>
      )}

      <input
        placeholder="Field name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ width: "100%", padding: 6, margin: "8px 0" }}
      />
      {result?.resolves && (
        <div style={{ color: "#15803d", fontSize: 13 }}>
          ✓ resolves to {result.count} — {result.values.slice(0, 3).join(", ")}
        </div>
      )}
      {error && <div style={{ color: "#b91c1c", fontSize: 13 }}>{error}</div>}
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button onClick={validate} disabled={busy}>
          {busy ? "…" : "Check"}
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
