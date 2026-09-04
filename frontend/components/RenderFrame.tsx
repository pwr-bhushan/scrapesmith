"use client";

import { useEffect, useState } from "react";

import { BatchInfo, ConfigFieldInput, getBatch, renderUrl } from "@/lib/api";
import FieldPanel from "@/components/FieldPanel";
import PickPopover, { PendingPick } from "@/components/PickPopover";

// Picker (design §5.2): rendered DOM in a sandboxed iframe, click-to-select via postMessage,
// popover to name+scope the field, right-hand field panel + save. Prev/Next navigates.
export default function RenderFrame({ batchId }: { batchId: string }) {
  const [batch, setBatch] = useState<BatchInfo | null>(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [pick, setPick] = useState<PendingPick | null>(null);
  const [fields, setFields] = useState<ConfigFieldInput[]>([]);

  useEffect(() => {
    getBatch(batchId).then(setBatch).catch((e) => setError(String(e)));
  }, [batchId]);

  useEffect(() => {
    function onMessage(e: MessageEvent) {
      if (e.data && e.data.type === "scrapesmith-pick") {
        setPick({ descriptor: e.data.descriptor, text: e.data.text, listParent: e.data.listParent });
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  if (error) return <p style={{ color: "#b91c1c" }}>{error}</p>;
  if (!batch) return <p>Loading…</p>;

  const total = batch.files.length;
  const current = batch.files[index];

  return (
    <div style={{ display: "flex", gap: 16 }}>
      <div style={{ flex: 1, display: "grid", gap: "0.75rem" }}>
        <div style={{ fontSize: 14, color: "#475569" }}>{current?.filename}</div>
        <iframe
          key={index}
          sandbox="allow-scripts"
          src={renderUrl(batchId, index)}
          style={{ width: "100%", height: "65vh", border: "1px solid #cbd5e1", borderRadius: 6 }}
          title={`file-${index}`}
        />
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>
            ◀ Prev
          </button>
          <span>
            File {index + 1} of {total}
          </span>
          <button
            onClick={() => setIndex((i) => Math.min(total - 1, i + 1))}
            disabled={index >= total - 1}
          >
            Next ▶
          </button>
        </div>
        {pick && (
          <PickPopover
            batchId={batchId}
            index={index}
            filename={current?.filename ?? ""}
            pick={pick}
            onConfirm={(f) => {
              setFields((prev) => [...prev, f]);
              setPick(null);
            }}
            onCancel={() => setPick(null)}
          />
        )}
      </div>
      <FieldPanel
        batchId={batchId}
        index={index}
        fields={fields}
        onRemove={(i) => setFields((prev) => prev.filter((_, j) => j !== i))}
      />
    </div>
  );
}
