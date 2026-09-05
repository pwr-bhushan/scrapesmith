"use client";

import { X } from "lucide-react";
import { useState } from "react";

import CanaryPanel from "@/components/CanaryPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, ErrorText } from "@/components/ui/empty";
import { Mono } from "@/components/ui/input";
import { CanaryResult, ConfigFieldInput, canary, saveConfig } from "@/lib/api";

// Right-hand field panel (§5.2): confirmed fields + Save config v1 + "Test on this file" (§5.5).
export default function FieldPanel({
  batchId,
  index,
  fields,
  onRemove,
}: {
  batchId: string;
  index: number;
  fields: ConfigFieldInput[];
  onRemove: (i: number) => void;
}) {
  const [saved, setSaved] = useState<string | null>(null);
  const [canaryResult, setCanaryResult] = useState<CanaryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setError(null);
    try {
      const r = await saveConfig(batchId, fields);
      setSaved(`Saved config v${r.version} · ${r.field_count} fields`);
    } catch (e) {
      setError(String(e));
    }
  }

  async function testFile() {
    setError(null);
    try {
      setCanaryResult(await canary(batchId, index));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="grid content-start gap-3 lg:sticky lg:top-16">
      <Card>
        <CardHeader>
          <CardTitle>Fields</CardTitle>
          {fields.length > 0 && <Badge>{fields.length}</Badge>}
        </CardHeader>
        <CardBody className="p-0">
          {fields.length === 0 ? (
            <Empty className="p-4">Click an element in the preview to add a field.</Empty>
          ) : (
            <ul className="divide-y divide-border">
              {fields.map((f, i) => (
                <li key={i} className="group flex items-start gap-2 px-4 py-2.5">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate text-sm font-medium">{f.name}</span>
                      <Badge>{f.type || "untyped"}</Badge>
                      {f.scope === "list" && <Badge tone="accent">list</Badge>}
                    </div>
                    <Mono className="mt-0.5 block truncate" title={f.selector}>
                      {f.selector}
                    </Mono>
                  </div>
                  <Button
                    size="icon"
                    variant="ghost"
                    aria-label={`Remove ${f.name}`}
                    className="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
                    onClick={() => onRemove(i)}
                  >
                    <X />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <div className="flex gap-2">
        <Button
          className="flex-1"
          variant="primary"
          onClick={save}
          disabled={fields.length === 0}
        >
          Save config
        </Button>
        <Button className="flex-1" onClick={testFile} disabled={fields.length === 0}>
          Test on this file
        </Button>
      </div>

      {saved && <p className="text-xs text-ok">{saved}</p>}
      {error && <ErrorText className="text-xs">{error}</ErrorText>}
      {canaryResult && <CanaryPanel result={canaryResult} />}
    </div>
  );
}
