const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("API unreachable");
  return res.json();
}

export default async function Home() {
  let status = "unknown";
  try {
    const health = await getHealth();
    status = health.status;
  } catch {
    status = "unreachable";
  }

  return (
    <main>
      <h1>Spotify Playlist Manager</h1>
      <p>Dashboard placeholder. API health: {status}</p>
    </main>
  );
}
