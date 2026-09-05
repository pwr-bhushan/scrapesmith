import AdvancedPanel from "@/components/AdvancedPanel";
import AppShell from "@/components/AppShell";
import BatchResults from "@/components/BatchResults";
import HealReview from "@/components/HealReview";
import RenderFrame from "@/components/RenderFrame";
import VersionPanel from "@/components/VersionPanel";

// Next 15: params is async.
export default async function PickPage({
  params,
}: {
  params: Promise<{ batchId: string }>;
}) {
  const { batchId } = await params;
  return (
    <AppShell context={<span className="font-mono">{batchId.slice(0, 8)}</span>}>
      <div className="grid gap-6">
        <RenderFrame batchId={batchId} />

        {/* Batch and heal read the same config, so they sit side by side rather than stacked —
            the drift check is only meaningful next to the failure rates that triggered it. */}
        <div className="grid gap-4 xl:grid-cols-2">
          <BatchResults batchId={batchId} />
          <HealReview batchId={batchId} />
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <VersionPanel batchId={batchId} />
          <AdvancedPanel batchId={batchId} index={0} />
        </div>
      </div>
    </AppShell>
  );
}
