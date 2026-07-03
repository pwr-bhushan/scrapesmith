import UploadForm from "@/components/UploadForm";

export default function Home() {
  return (
    <main style={{ fontFamily: "system-ui", padding: "2rem" }}>
      <h1>scrapesmith</h1>
      <p style={{ color: "#475569" }}>Upload HTML to build or test an extraction config.</p>
      <UploadForm />
    </main>
  );
}
