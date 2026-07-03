"use client";

import { useEffect, useState } from "react";

import { BatchInfo, getBatch, renderUrl } from "@/lib/api";

// Picker shell (design §5.2, Phase 1 subset): rendered DOM in a sandboxed iframe + Prev/Next.
// Click-to-select is Phase 2.
export default function RenderFrame({ batchId }: { batchId: string }) {
  const [batch, setBatch] = useState<BatchInfo | null>(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getBatch(batchId).then(setBatch).catch((e) => setError(String(e)));
  }, [batchId]);

  if (error) return <p style={{ color: "#b91c1c" }}>{error}</p>;
  if (!batch) return <p>Loading…</p>;

  const total = batch.files.length;
  const current = batch.files[index];

  return (
    <div style={{ display: "grid", gap: "0.75rem" }}>
      <div style={{ fontSize: 14, color: "#475569" }}>
        {batch.domain_id} • {current?.filename}
      </div>
      <iframe
        // allow-scripts (for our overlay) WITHOUT allow-same-origin: content stays sandboxed.
        sandbox="allow-scripts"
        src={renderUrl(batchId, index)}
        style={{ width: "100%", height: "70vh", border: "1px solid #cbd5e1", borderRadius: 6 }}
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
    </div>
  );
}
