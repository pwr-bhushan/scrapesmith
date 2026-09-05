import AppShell from "@/components/AppShell";
import UploadForm from "@/components/UploadForm";

export default function Home() {
  return (
    <AppShell>
      <div className="mx-auto max-w-[560px] py-10">
        <h1 className="text-xl font-semibold tracking-tight">Upload HTML</h1>
        <p className="mt-1 text-sm text-muted">
          Build an extraction config by clicking fields in a rendered page, then run it across the
          batch.
        </p>
        <div className="mt-6">
          <UploadForm />
        </div>
      </div>
    </AppShell>
  );
}
