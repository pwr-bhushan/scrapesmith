import * as React from "react";

import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-[var(--radius-control)] border border-border-strong bg-surface",
        "px-2.5 text-sm text-ink placeholder:text-faint",
        "focus-visible:border-accent disabled:opacity-45",
        className,
      )}
      {...props}
    />
  );
}

export function Select({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-9 rounded-[var(--radius-control)] border border-border-strong bg-surface",
        "px-2 text-sm text-ink focus-visible:border-accent disabled:opacity-45",
        className,
      )}
      {...props}
    />
  );
}

/** Selectors, extracted values and anchors are always mono — they are literals, not prose. */
export function Mono({ className, ...props }: React.ComponentProps<"code">) {
  return (
    <code
      className={cn("font-mono text-[12px] leading-tight text-muted", className)}
      {...props}
    />
  );
}
