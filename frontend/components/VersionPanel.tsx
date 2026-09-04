"use client";

import { useEffect, useState } from "react";

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

  return (
    <div style={{ marginTop: 16, borderTop: "1px solid #cbd5e1", paddingTop: 12 }}>
      <h3>Versions</h3>
      {versions.length === 0 && <p style={{ color: "#94a3b8" }}>No versions yet — save a config.</p>}
      <ul style={{ listStyle: "none", padding: 0, fontSize: 13 }}>
        {versions.map((v) => (
          <li key={v.id} style={{ marginBottom: 4 }}>
            v{v.version} · {v.created_by ?? "user"} · {v.field_count} fields{" "}
            <button style={{ fontSize: 11 }} onClick={() => pin(v.version)}>
              Pin
            </button>
          </li>
        ))}
      </ul>
      {versions.length >= 2 && <button onClick={showDiff}>Diff last two</button>}
      {msg && <p style={{ color: "#15803d" }}>{msg}</p>}
      {diff && (
        <div style={{ fontSize: 13, marginTop: 8 }}>
          {diff.added.length > 0 && <div>+ added: {diff.added.join(", ")}</div>}
          {diff.removed.length > 0 && <div>− removed: {diff.removed.join(", ")}</div>}
          {Object.entries(diff.changed).map(([name, deltas]) => (
            <div key={name}>
              ~ {name}:{" "}
              {Object.entries(deltas).map(([k, [a, b]]) => (
                <span key={k}>
                  {k} {String(a)} → {String(b)};{" "}
                </span>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
