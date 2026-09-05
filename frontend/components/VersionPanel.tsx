"use client";

import { GitCompare, Pin } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty } from "@/components/ui/empty";
import {
  CONFIG_VERSION_CREATED,
  VersionDiff,
  VersionInfo,
  diffVersions,
  getBatch,
  listVersions,
  pinBatch,
} from "@/lib/api";

// Version list + diff + pin (design §11 / §5.7 advanced).
export default function VersionPanel({ batchId }: { batchId: string }) {
  const [domainId, setDomainId] = useState<string | null>(null);
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [diff, setDiff] = useState<VersionDiff | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  async function refresh(dId: string) {
    setVersions(await listVersions(dId));
  }

  useEffect(() => {
    let dId: string | null = null;
    const reload = () => dId && refresh(dId);
    getBatch(batchId).then((b) => {
      dId = b.domain_id;
      setDomainId(b.domain_id);
      refresh(b.domain_id);
    });
    // Saving a config or accepting a heal happens in a sibling island, so the list would
    // otherwise stay stuck on whatever existed at mount.
    window.addEventListener(CONFIG_VERSION_CREATED, reload);
    return () => window.removeEventListener(CONFIG_VERSION_CREATED, reload);
  }, [batchId]);

  async function showDiff() {
    if (!domainId || versions.length < 2) return;
    const a = versions[versions.length - 2].version;
    const b = versions[versions.length - 1].version;
    setDiff(await diffVersions(domainId, a, b));
  }

  async function pin(v: number) {
    const r = await pinBatch(batchId, v);
    setMsg(`Pinned batch to v${r.pinned_version}`);
  }

  const latest = versions.length ? versions[versions.length - 1].version : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Versions</CardTitle>
        {versions.length >= 2 && (
          <Button size="sm" variant="ghost" onClick={showDiff}>
            <GitCompare /> Diff last two
          </Button>
        )}
      </CardHeader>

      <CardBody className={versions.length ? "p-0" : undefined}>
        {versions.length === 0 ? (
          <Empty>No versions yet — save a config to create v1.</Empty>
        ) : (
          <ul className="divide-y divide-border">
            {versions.map((v) => (
              <li key={v.id} className="group flex items-center gap-2 px-4 py-2">
                <span className="w-10 shrink-0 font-mono text-xs font-medium">v{v.version}</span>
                <span className="flex-1 truncate text-xs text-muted">
                  {v.created_by ?? "user"} · {v.field_count} fields
                </span>
                {v.version === latest && <Badge tone="accent">latest</Badge>}
                <Button
                  size="sm"
                  variant="ghost"
                  className="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
                  onClick={() => pin(v.version)}
                >
                  <Pin /> Pin
                </Button>
              </li>
            ))}
          </ul>
        )}

        {(msg || diff) && (
          <div className="border-t border-border px-4 py-3">
            {msg && <p className="text-xs text-ok">{msg}</p>}
            {diff && (
              <dl className="mt-1 grid gap-1 font-mono text-[11px]">
                {diff.added.length > 0 && (
                  <div className="text-ok">+ {diff.added.join(", ")}</div>
                )}
                {diff.removed.length > 0 && (
                  <div className="text-danger">− {diff.removed.join(", ")}</div>
                )}
                {Object.entries(diff.changed).map(([name, deltas]) => (
                  <div key={name} className="text-muted">
                    ~ {name}:{" "}
                    {Object.entries(deltas)
                      .map(([k, [a, b]]) => `${k} ${String(a)} → ${String(b)}`)
                      .join("; ")}
                  </div>
                ))}
              </dl>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
}
