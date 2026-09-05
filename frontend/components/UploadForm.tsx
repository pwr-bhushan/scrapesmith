"use client";

import { UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ErrorText } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { uploadBatch } from "@/lib/api";

// Upload screen (design §5.1): file + domain/page_type/JS toggle/notes -> POST /upload -> picker.
export default function UploadForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const form = new FormData(e.currentTarget);
      // unchecked checkbox omits the field; normalize to explicit boolean string
      form.set("render_js", form.get("render_js") ? "true" : "false");
      const result = await uploadBatch(form);
      router.push(`/pick/${result.batch_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-4">
      <label
        className="group flex cursor-pointer flex-col items-center gap-2 rounded-[var(--radius-card)]
          border border-dashed border-border-strong bg-surface px-6 py-8 text-center
          transition-colors hover:border-accent hover:bg-accent-soft/40"
      >
        <UploadCloud className="size-5 text-faint group-hover:text-accent" />
        <span className="text-sm font-medium">
          {filename ?? "Drop HTML, .gz or .zip here"}
        </span>
        <span className="text-xs text-muted">or click to browse</span>
        <input
          type="file"
          name="file"
          accept=".html,.htm,.gz,.zip"
          required
          className="sr-only"
          onChange={(e) => setFilename(e.target.files?.[0]?.name ?? null)}
        />
      </label>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Domain">
          <Input name="host" placeholder="amazon.in" required />
        </Field>
        <Field label="Page type">
          <Input name="page_type" placeholder="product_listing" required />
        </Field>
      </div>

      <Field label="Notes">
        <Input name="notes" placeholder="optional" />
      </Field>

      <label className="flex items-start gap-2.5 rounded-[var(--radius-control)] border border-border bg-surface p-3">
        <input
          type="checkbox"
          name="render_js"
          defaultChecked
          className="mt-0.5 size-4 accent-[var(--color-accent)]"
        />
        <span className="text-sm">
          Render JS
          <span className="block text-xs text-muted">
            Run page scripts — slower, more faithful
          </span>
        </span>
      </label>

      {error && <ErrorText>{error}</ErrorText>}

      <Button type="submit" variant="primary" disabled={busy} className="justify-self-start">
        {busy ? "Uploading…" : "Continue"}
      </Button>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1.5">
      <span className="text-xs font-medium text-muted">{label}</span>
      {children}
    </label>
  );
}
