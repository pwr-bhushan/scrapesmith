import AdvancedPanel from "@/components/AdvancedPanel";
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
    <main style={{ fontFamily: "system-ui", padding: "2rem" }}>
      <h1 style={{ fontSize: 20 }}>Pick fields</h1>
      <RenderFrame batchId={batchId} />
      <BatchResults batchId={batchId} />
      <HealReview batchId={batchId} />
      <VersionPanel batchId={batchId} />
      <AdvancedPanel batchId={batchId} index={0} />
    </main>
  );
}
