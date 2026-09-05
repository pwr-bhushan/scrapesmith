"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import FieldPanel from "@/components/FieldPanel";
import PickPopover, { PendingPick } from "@/components/PickPopover";
import { Button } from "@/components/ui/button";
import { ErrorText } from "@/components/ui/empty";
import { BatchInfo, ConfigFieldInput, getBatch, renderUrl } from "@/lib/api";

// Picker (design §5.2): rendered DOM in a sandboxed iframe, click-to-select via postMessage,
// popover to name+scope the field, right-hand field panel + save. Prev/Next navigates.
export default function RenderFrame({ batchId }: { batchId: string }) {
  const [batch, setBatch] = useState<BatchInfo | null>(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [pick, setPick] = useState<PendingPick | null>(null);
  const [fields, setFields] = useState<ConfigFieldInput[]>([]);
  const frameRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    getBatch(batchId).then(setBatch).catch((e) => setError(String(e)));
  }, [batchId]);

  useEffect(() => {
    function onMessage(e: MessageEvent) {
      if (e.data && e.data.type === "scrapesmith-pick") {
        // render.py posts a rect relative to the iframe viewport; add the iframe's own position
        // so the popover can sit against the element the user actually clicked.
        const box = frameRef.current?.getBoundingClientRect();
        const r = e.data.rect;
        setPick({
          descriptor: e.data.descriptor,
          text: e.data.text,
          listParent: e.data.listParent,
          anchor:
            box && r
              ? { top: box.top + r.top, left: box.left + r.left, width: r.width, height: r.height }
              : null,
        });
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  if (error) return <ErrorText>{error}</ErrorText>;
  if (!batch) return <p className="text-sm text-muted">Loading…</p>;

  const total = batch.files.length;
  const current = batch.files[index];

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="grid content-start gap-3">
        <div className="flex items-center justify-between gap-3">
          <span className="truncate font-mono text-xs text-muted">{current?.filename}</span>
          <div className="flex shrink-0 items-center gap-1">
            <Button
              size="icon"
              variant="ghost"
              aria-label="Previous file"
              onClick={() => setIndex((i) => Math.max(0, i - 1))}
              disabled={index === 0}
            >
              <ChevronLeft />
            </Button>
            <span className="tabular-nums text-xs text-muted">
              {index + 1} / {total}
            </span>
            <Button
              size="icon"
              variant="ghost"
              aria-label="Next file"
              onClick={() => setIndex((i) => Math.min(total - 1, i + 1))}
              disabled={index >= total - 1}
            >
              <ChevronRight />
            </Button>
          </div>
        </div>

        <iframe
          key={index}
          ref={frameRef}
          sandbox="allow-scripts"
          src={renderUrl(batchId, index)}
          className="h-[70vh] w-full rounded-[var(--radius-card)] border border-border bg-surface"
          title={`file-${index}`}
        />
        <p className="text-xs text-faint">
          Hover to highlight, click to capture a field. The page renders in a sandboxed,
          egress-blocked frame.
        </p>

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
