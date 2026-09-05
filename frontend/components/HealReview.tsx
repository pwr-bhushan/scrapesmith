"use client";

import { ArrowRight, Stethoscope } from "lucide-react";
import { useState } from "react";

import { Badge, toneFor } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, ErrorText } from "@/components/ui/empty";
import { Table, Td, Th } from "@/components/ui/table";
import { HealProposal, HealProposeResult, healAccept, healPropose } from "@/lib/api";

// The anchor cell has to say whether the anchor was *checked*, not just what it holds. An anchor
// is an assertion about one page; when that page isn't in this drift cluster the check is
// inapplicable (anchor_ok === null) and showing a bare value next to "healed" reads as a
// contradiction — the proposal is a different product, so of course it differs.
type AnchorVerdict = "match" | "diverged" | "not-checked" | "none";

function anchorVerdict(p: HealProposal): AnchorVerdict {
  if (!p.anchor) return "none";
  if (p.anchor_ok === true) return "match";
  if (p.anchor_ok === false) return "diverged";
  return "not-checked";
}

/** Before → after on the *value*, which is what the operator is being asked to judge.
 *  Selectors are shown underneath as supporting evidence, not as the decision. */
function ValueDiff({ p }: { p: HealProposal }) {
  const verdict = anchorVerdict(p);
  const changed = verdict === "diverged";
  return (
    <div className="flex items-center gap-2 font-mono text-xs">
      <span className={changed ? "text-danger line-through" : "text-muted"}>
        {p.anchor ?? "—"}
      </span>
      <ArrowRight className="size-3 shrink-0 text-faint" />
      <span className={changed ? "font-medium text-ink" : "text-ink"}>{p.value ?? "—"}</span>
    </div>
  );
}

function AnchorBadge({ p }: { p: HealProposal }) {
  const verdict = anchorVerdict(p);
  if (verdict === "match") return <Badge tone="ok">anchor match</Badge>;
  if (verdict === "diverged") return <Badge tone="danger">anchor diverged</Badge>;
  if (verdict === "not-checked")
    return (
      <Badge title="The anchor's own page is not in this drift cluster, so the check is inapplicable here.">
        not in this cluster
      </Badge>
    );
  return <Badge>no anchor</Badge>;
}

// Drift + value-first heal review (design §5.6/§5.7): show proposed value vs anchor, suspect flag,
// accept per field. Values first, selectors are secondary.
export default function HealReview({ batchId }: { batchId: string }) {
  const [result, setResult] = useState<HealProposeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [accepted, setAccepted] = useState<Record<string, string>>({});
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function check() {
    setError(null);
    setSavedMsg(null);
    setBusy(true);
    try {
      const r = await healPropose(batchId);
      setResult(r);
      // pre-select healed fields
      const pre: Record<string, string> = {};
      r.clusters?.forEach((cl) =>
        Object.entries(cl.proposals).forEach(([name, p]) => {
          if (p.status === "healed") pre[name] = p.selector;
        })
      );
      setAccepted(pre);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function accept() {
    try {
      const r = await healAccept(batchId, accepted);
      setSavedMsg(`Applied heal → config v${r.version} (${r.healed.join(", ")})`);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Heal</CardTitle>
        <Button size="sm" onClick={check} disabled={busy}>
          <Stethoscope /> {busy ? "Checking…" : "Check for drift"}
        </Button>
      </CardHeader>

      <CardBody className={result?.triggered ? "grid gap-3" : undefined}>
        {error && <ErrorText>{error}</ErrorText>}

        {!result && !error && (
          <Empty>
            Heal triggers when any field fails on 30% or more of the batch. A proposal only counts
            if it reproduces the value you originally confirmed.
          </Empty>
        )}

        {result && !result.triggered && (
          <p className="text-sm text-ok">No drift — every field is under the threshold.</p>
        )}

        {result?.triggered && (
          <>
            <p className="text-sm">
              <span className="text-muted">Drift detected on</span>{" "}
              <span className="font-medium">{result.failing?.join(", ")}</span>
            </p>

            {result.clusters?.map((cl) => (
              <div key={cl.hash} className="overflow-hidden rounded-[var(--radius-control)] border border-border">
                <div className="flex items-center justify-between gap-2 border-b border-border bg-subtle px-3 py-1.5">
                  <span className="font-mono text-[11px] text-muted">
                    cluster {cl.hash.slice(0, 8)} · {cl.size} file{cl.size === 1 ? "" : "s"}
                  </span>
                  <Badge tone={cl.model === "unavailable" ? "warn" : "neutral"}>{cl.model}</Badge>
                </div>

                {cl.model === "unavailable" ? (
                  <p className="px-3 py-3 text-sm text-warn">
                    No heal model configured — set <code className="font-mono">ANTHROPIC_API_KEY</code>{" "}
                    or <code className="font-mono">OLLAMA_HOST</code>.
                  </p>
                ) : (
                  <Table>
                    <thead>
                      <tr>
                        <Th className="w-10" />
                        <Th>Field</Th>
                        <Th>Confirmed value → proposed value</Th>
                        <Th>Check</Th>
                        <Th>Gate</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(cl.proposals).map(([name, p]) => (
                        <tr key={name} className="last:[&>td]:border-b-0">
                          <Td>
                            <input
                              type="checkbox"
                              aria-label={`Accept ${name}`}
                              className="size-4 accent-[var(--color-accent)]"
                              disabled={p.status === "still_broken"}
                              checked={accepted[name] === p.selector}
                              onChange={(e) =>
                                setAccepted((prev) => {
                                  const next = { ...prev };
                                  if (e.target.checked) next[name] = p.selector;
                                  else delete next[name];
                                  return next;
                                })
                              }
                            />
                          </Td>
                          <Td className="font-medium">{name}</Td>
                          <Td>
                            <ValueDiff p={p} />
                            <code className="mt-1 block truncate font-mono text-[11px] text-faint">
                              {p.selector}
                            </code>
                          </Td>
                          <Td>
                            <AnchorBadge p={p} />
                          </Td>
                          <Td>
                            <Badge tone={toneFor(p.status)}>{p.status}</Badge>
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                )}
              </div>
            ))}

            <div className="flex items-center gap-3">
              <Button
                variant="primary"
                onClick={accept}
                disabled={Object.keys(accepted).length === 0}
              >
                Accept selected ({Object.keys(accepted).length})
              </Button>
              {savedMsg && <p className="text-xs text-ok">{savedMsg}</p>}
            </div>
          </>
        )}
      </CardBody>
    </Card>
  );
}
