"use client";

import * as Popover from "@radix-ui/react-popover";
import { Check, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Mono, Select } from "@/components/ui/input";
import {
  Descriptor,
  getPresets,
  infer,
  InferResult,
  validatePick,
  ValidateResult,
} from "@/lib/api";

/** Where in the page the clicked element sits, in viewport coordinates. Null when the render
 *  frame could not supply geometry, in which case the popover centres instead of anchoring. */
export interface PickAnchor {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface PendingPick {
  descriptor: Descriptor;
  text: string;
  listParent: { selector: string; count: number } | null;
  anchor: PickAnchor | null;
}

// Click popover (design §5.3): inferred type + confidence, Change dropdown, ✨ opt-in LLM, scope, name.
export default function PickPopover({
  batchId,
  index,
  filename,
  pick,
  onConfirm,
  onCancel,
}: {
  batchId: string;
  index: number;
  filename: string;
  pick: PendingPick;
  onConfirm: (field: {
    name: string;
    selector: string;
    scope: string;
    list_parent_selector: string | null;
    type: string | null;
    dq: Record<string, unknown> | null;
    anchor: { value: string; file?: string; fingerprint?: unknown } | null;
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

  const canConfirm = Boolean(result?.resolves && result.selector && name.trim());

  function confirm() {
    if (!canConfirm || !result?.selector) return;
    onConfirm({
      name: name.trim(),
      selector: result.selector,
      scope,
      list_parent_selector: result.list_parent_selector,
      type: chosenType || inferred?.type || null,
      dq: chosenType === inferred?.type ? inferred?.dq ?? null : null,
      // anchor (§10): snapshot the resolved value + descriptor fingerprint at confirm, and the
      // page it was read off — heal compares the anchor on that page, not on whichever file
      // happens to represent the drift cluster.
      anchor: result.values[0]
        ? { value: result.values[0], file: filename, fingerprint: pick.descriptor }
        : null,
    });
  }

  const confPct = inferred ? Math.round(inferred.confidence * 100) : 0;
  const a = pick.anchor;

  return (
    <Popover.Root open onOpenChange={(o) => !o && onCancel()}>
      {/* Anchored to the element the user clicked, via a zero-size element pinned at its rect.
          Captured at click time and not re-anchored on scroll — see render.py's picker script. */}
      <Popover.Anchor
        style={
          a
            ? {
                position: "fixed",
                top: a.top,
                left: a.left,
                width: a.width,
                height: a.height,
                pointerEvents: "none",
              }
            : { position: "fixed", top: "40%", left: "50%" }
        }
      />
      <Popover.Portal>
        <Popover.Content
          side="bottom"
          align="start"
          sideOffset={8}
          collisionPadding={16}
          onOpenAutoFocus={(e) => e.preventDefault()}
          onKeyDown={(e) => {
            if (e.key === "Enter" && canConfirm) {
              e.preventDefault();
              confirm();
            }
          }}
          className="z-50 w-[320px] rounded-[var(--radius-card)] border border-border-strong
            bg-surface p-3.5 shadow-[0_8px_28px_-8px_rgba(26,26,25,0.28)]"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                {inferred?.type ? (
                  <>
                    <Badge tone="accent">{inferred.type}</Badge>
                    <span className="tabular-nums text-[11px] text-muted">{confPct}%</span>
                  </>
                ) : (
                  <Badge>couldn&rsquo;t auto-detect</Badge>
                )}
              </div>
              <p className="mt-1.5 truncate font-mono text-xs text-ink" title={pick.text}>
                {pick.text || "(empty)"}
              </p>
            </div>
            <Button size="icon" variant="ghost" aria-label="Cancel" onClick={onCancel}>
              <X />
            </Button>
          </div>

          {inferred?.source === "llm_unavailable" && (
            <p className="mt-2 text-[11px] text-warn">✨ needs ANTHROPIC_API_KEY</p>
          )}

          <div className="mt-3 grid gap-2.5">
            <label className="grid gap-1.5">
              <span className="text-[11px] font-medium text-muted">Field name</span>
              <Input
                autoFocus
                placeholder="e.g. price"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>

            <label className="grid gap-1.5">
              <span className="text-[11px] font-medium text-muted">Type</span>
              <div className="flex gap-1.5">
                <Select
                  className="flex-1"
                  value={chosenType}
                  onChange={(e) => setChosenType(e.target.value)}
                >
                  <option value="">(none)</option>
                  {presets.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </Select>
                <Button
                  size="icon"
                  variant="ghost"
                  className="size-9"
                  onClick={askAI}
                  disabled={busy}
                  title="Ask AI (opt-in)"
                  aria-label="Ask AI to classify this field"
                >
                  <Sparkles />
                </Button>
              </div>
            </label>

            <fieldset className="grid gap-1">
              <legend className="mb-1 text-[11px] font-medium text-muted">Scope</legend>
              <Radio
                checked={scope === "single"}
                onChange={() => setScope("single")}
                label="Just this one"
              />
              {pick.listParent && (
                <Radio
                  checked={scope === "list"}
                  onChange={() => setScope("list")}
                  label={`All ${pick.listParent.count} similar items`}
                />
              )}
            </fieldset>
          </div>

          {result?.resolves && (
            <div className="mt-3 rounded-[var(--radius-control)] bg-ok-soft px-2.5 py-2">
              <p className="flex items-center gap-1 text-xs font-medium text-ok">
                <Check className="size-3.5" /> resolves to {result.count}
              </p>
              <Mono className="mt-1 block truncate text-ok">
                {result.values.slice(0, 3).join(", ")}
              </Mono>
            </div>
          )}
          {error && <p className="mt-3 text-xs text-danger">{error}</p>}

          <div className="mt-3 flex gap-2">
            <Button className="flex-1" onClick={validate} disabled={busy}>
              {busy ? "Checking…" : "Check"}
            </Button>
            <Button
              className="flex-1"
              variant="primary"
              onClick={confirm}
              disabled={!canConfirm}
            >
              Confirm
            </Button>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function Radio({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm">
      <input
        type="radio"
        checked={checked}
        onChange={onChange}
        className="size-3.5 accent-[var(--color-accent)]"
      />
      {label}
    </label>
  );
}
