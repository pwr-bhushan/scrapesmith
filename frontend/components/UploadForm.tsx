"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { uploadBatch } from "@/lib/api";

// Upload screen (design §5.1): file + domain/page_type/JS toggle/notes -> POST /upload -> picker.
export default function UploadForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.75rem", maxWidth: 520 }}>
      <label style={box}>
        ⬆ Drop HTML / .gz / .zip here — or click to browse
        <input type="file" name="file" accept=".html,.htm,.gz,.zip" required style={{ marginTop: 8 }} />
      </label>

      <label>
        Domain
        <input name="host" placeholder="amazon.in" required style={input} />
      </label>
      <label>
        Page type
        <input name="page_type" placeholder="product_listing" required style={input} />
      </label>
      <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input type="checkbox" name="render_js" defaultChecked />
        Render JS (run page scripts — slower, more faithful)
      </label>
      <label>
        Notes
        <input name="notes" placeholder="optional" style={input} />
      </label>

      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}
      <button type="submit" disabled={busy} style={button}>
        {busy ? "Uploading…" : "Continue →"}
      </button>
    </form>
  );
}

const box: React.CSSProperties = {
  display: "block",
  border: "2px dashed #94a3b8",
  borderRadius: 8,
  padding: "1.5rem",
  textAlign: "center",
};
const input: React.CSSProperties = { display: "block", width: "100%", padding: 6, marginTop: 4 };
const button: React.CSSProperties = {
  padding: "0.6rem 1rem",
  background: "#4f46e5",
  color: "white",
  border: "none",
  borderRadius: 6,
  cursor: "pointer",
};
