"use client";

import { Badge, toneFor } from "@/components/ui/badge";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { CanaryResult } from "@/lib/api";

// Canary result panel (design §5.5): one file parsed, per-field value + DQ status + anchor match.
export default function CanaryPanel({ result }: { result: CanaryResult }) {
  const names = Object.keys(result.field_status);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Canary</CardTitle>
        <span className="truncate font-mono text-[11px] text-faint">
          {result.filename} · v{result.config_version}
        </span>
      </CardHeader>
      <CardBody className="p-0">
        <Table>
          <thead>
            <tr>
              <Th>Field</Th>
              <Th>Value</Th>
              <Th>DQ</Th>
              <Th>Anchor</Th>
            </tr>
          </thead>
          <tbody>
            {names.map((n) => {
              const status = result.field_status[n];
              const value = result.data[n];
              const anchor = result.anchor_ok[n];
              return (
                <tr key={n} className="last:[&>td]:border-b-0">
                  <Td className="font-medium">{n}</Td>
                  <Td className="max-w-[160px] truncate font-mono text-xs text-muted">
                    {Array.isArray(value)
                      ? `[${value.length}] ${value.slice(0, 3).join(", ")}`
                      : String(value ?? "—")}
                  </Td>
                  <Td>
                    <Badge tone={toneFor(status)}>{status}</Badge>
                  </Td>
                  <Td className="text-xs">
                    {anchor === null ? (
                      <span className="text-faint">n/a</span>
                    ) : anchor ? (
                      <span className="text-ok">match</span>
                    ) : (
                      <span className="text-danger">diverged</span>
                    )}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </CardBody>
    </Card>
  );
}
