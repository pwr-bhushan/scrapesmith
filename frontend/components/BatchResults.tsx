"use client";

import { Download, Play } from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, ErrorText } from "@/components/ui/empty";
import { Table, Td, Th } from "@/components/ui/table";
import {
  BatchResultsData,
  batchResults,
  exportCsvUrl,
  exportJsonUrl,
  jobStatus,
  startBatch,
} from "@/lib/api";

// Batch results screen (design §5.8): run async batch, watch progress, per-field rates, export.
export default function BatchResults({ batchId }: { batchId: string }) {
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [state, setState] = useState<string>("");
  const [results, setResults] = useState<BatchResultsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  async function run() {
    setError(null);
    setResults(null);
    try {
      const { job_id } = await startBatch(batchId);
      setState("queued");
      timer.current = setInterval(async () => {
        try {
          const s = await jobStatus(job_id);
          setState(s.state);
          setProgress(s.progress);
          if (s.state === "done" || s.state === "failed") {
            if (timer.current) clearInterval(timer.current);
            if (s.state === "done") setResults(await batchResults(batchId));
            else setError(s.error || "batch failed");
          }
        } catch (e) {
          if (timer.current) clearInterval(timer.current);
          setError(String(e));
        }
      }, 500);
    } catch (e) {
      setError(String(e));
    }
  }

  const running = state === "running" || state === "queued";
  const pct = progress && progress.total ? Math.round((progress.done / progress.total) * 100) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Batch</CardTitle>
        <div className="flex items-center gap-2">
          {results && (
            <>
              <Button size="sm" variant="ghost" asChild>
                <a href={exportCsvUrl(batchId)}>
                  <Download /> CSV
                </a>
              </Button>
              <Button size="sm" variant="ghost" asChild>
                <a href={exportJsonUrl(batchId)}>
                  <Download /> JSON
                </a>
              </Button>
            </>
          )}
          <Button size="sm" onClick={run} disabled={running}>
            <Play /> {running ? "Running…" : "Run batch"}
          </Button>
        </div>
      </CardHeader>

      <CardBody className={results ? "p-0" : undefined}>
        {running || (state && !results) ? (
          <div className="p-4">
            <div className="mb-1.5 flex items-baseline justify-between text-xs text-muted">
              <span>{state}</span>
              <span className="tabular-nums">
                {progress?.done ?? 0}/{progress?.total ?? 0}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-subtle">
              <div
                className="h-full rounded-full bg-accent transition-[width] duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        ) : null}

        {error && <ErrorText className="p-4">{error}</ErrorText>}

        {!state && !error && (
          <Empty>Run the batch to see per-field failure rates across every file.</Empty>
        )}

        {results && (
          <Table>
            <thead>
              <tr>
                <Th>Field</Th>
                <Th className="text-right">Failures</Th>
                <Th className="text-right">In scope</Th>
                <Th className="text-right">Rate</Th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(results.field_rates).map(([name, r]) => (
                <tr key={name} className="last:[&>td]:border-b-0">
                  <Td className="font-medium">{name}</Td>
                  <Td className="text-right tabular-nums text-muted">{r.failures}</Td>
                  <Td className="text-right tabular-nums text-muted">{r.in_scope}</Td>
                  <Td className="text-right">
                    {/* 30% is the heal trigger threshold (§9) — the badge turns at the same
                        number the backend acts on, so the UI never disagrees with the trigger. */}
                    <Badge tone={r.failure_rate >= 0.3 ? "danger" : "ok"}>
                      {(r.failure_rate * 100).toFixed(0)}%
                    </Badge>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </CardBody>
    </Card>
  );
}
