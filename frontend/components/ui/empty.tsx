import * as React from "react";

import { cn } from "@/lib/utils";

/** Shared empty state, so "nothing here yet" reads the same in every panel. */
export function Empty({ className, ...props }: React.ComponentProps<"p">) {
  return <p className={cn("text-sm text-faint", className)} {...props} />;
}

export function ErrorText({ className, ...props }: React.ComponentProps<"p">) {
  return <p className={cn("text-sm text-danger", className)} {...props} />;
}
