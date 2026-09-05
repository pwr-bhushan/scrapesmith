import type { ReactNode } from "react";

/** Page chrome: a thin header strip and one centred column.
 *
 * The old pages set `padding: 2rem` on <main> and nothing else, so content ran flush to the
 * window edge at any width. Everything routes through here now so the two screens agree on
 * gutter, measure and header height. */
export default function AppShell({
  context,
  children,
}: {
  context?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-20 border-b border-border bg-canvas/85 backdrop-blur">
        <div className="mx-auto flex h-12 w-full max-w-[1400px] items-center gap-3 px-6">
          <a href="/" className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-accent" aria-hidden />
            <span className="text-sm font-semibold tracking-tight">scrapesmith</span>
          </a>
          {context ? (
            <div className="ml-auto flex items-center gap-2 text-xs text-muted">{context}</div>
          ) : null}
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-6 py-6">{children}</main>
    </div>
  );
}
