import type { ReactNode } from "react";

export const metadata = {
  title: "scrapesmith",
  description: "Self-healing HTML parser",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
