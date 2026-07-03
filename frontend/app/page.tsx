import { getHealth } from "@/lib/api";

// Server component: fetch /health at request time. Phase 0.5 hello page.
export default async function Home() {
  let status = "unknown";
  try {
    status = (await getHealth()).status;
  } catch {
    status = "unreachable";
  }

  return (
    <main style={{ fontFamily: "system-ui", padding: "2rem" }}>
      <h1>scrapesmith</h1>
      <p>
        API health: <strong>{status}</strong>
      </p>
    </main>
  );
}
