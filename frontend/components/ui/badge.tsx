import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const badge = cva(
  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
  {
    variants: {
      tone: {
        neutral: "bg-subtle text-muted",
        ok: "bg-ok-soft text-ok",
        warn: "bg-warn-soft text-warn",
        danger: "bg-danger-soft text-danger",
        accent: "bg-accent-soft text-accent",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export function Badge({
  className,
  tone,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badge>) {
  return <span className={cn(badge({ tone }), className)} {...props} />;
}

/** Map a DQ status or heal gate verdict to a tone, so every table agrees on what red means. */
export function toneFor(status: string): "ok" | "warn" | "danger" | "neutral" {
  if (status === "ok" || status === "healed") return "ok";
  if (status === "suspect") return "warn";
  if (status === "still_broken" || status === "empty") return "danger";
  return status.endsWith("_fail") ? "danger" : "neutral";
}
