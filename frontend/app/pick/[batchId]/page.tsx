import RenderFrame from "@/components/RenderFrame";

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
    </main>
  );
}
