"use client";

import { ChevronDown, Terminal } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorText } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
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
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <Terminal className="size-3.5" /> Advanced
        </CardTitle>
        <Button size="sm" variant="ghost" onClick={() => setOpen((o) => !o)}>
          {open ? "Hide" : "Show"}
          <ChevronDown className={open ? "rotate-180 transition-transform" : "transition-transform"} />
        </Button>
      </CardHeader>

      {open && (
        <CardBody className="grid gap-5">
          <section className="grid gap-2">
            <h3 className="text-xs font-medium text-muted">
              Custom selector check — file {index + 1}
            </h3>
            <div className="flex gap-2">
              <Input
                className="font-mono text-xs"
                placeholder="css=… or xpath=…"
                value={sel}
                onChange={(e) => setSel(e.target.value)}
              />
              <Button onClick={runCheck}>Check</Button>
            </div>
            {check && (
              <p
                className={`font-mono text-xs ${check.count ? "text-ok" : "text-danger"}`}
              >
                resolves to {check.count}
                {check.count > 0 && ` — ${check.values.slice(0, 3).join(", ")}`}
              </p>
            )}
          </section>

          <section className="grid gap-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-medium text-muted">Raw JSON config — fields[]</h3>
              <Button size="sm" variant="ghost" onClick={load}>
                Load current
              </Button>
            </div>
            <textarea
              value={json}
              onChange={(e) => setJson(e.target.value)}
              rows={12}
              spellCheck={false}
              className="w-full rounded-[var(--radius-control)] border border-border-strong bg-surface
                p-2.5 font-mono text-xs leading-relaxed text-ink placeholder:text-faint
                focus-visible:border-accent"
              placeholder='[{"name":"price","selector":"css=[data-price]","scope":"single","dq":{"required":true,"parses_as":"number"}}]'
            />
            <Button variant="primary" className="justify-self-start" onClick={validateAndSave}>
              Validate &amp; save
            </Button>
          </section>

          {msg && <p className="text-xs text-ok">{msg}</p>}
          {error && <ErrorText className="text-xs">{error}</ErrorText>}
        </CardBody>
      )}
    </Card>
  );
}
