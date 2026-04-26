const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function getHealth(): Promise<{ status: string } | null> {
  try {
    const res = await fetch(`${API_BASE}/healthz`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json() as Promise<{ status: string }>;
  } catch {
    return null;
  }
}

export default async function HomePage() {
  const health = await getHealth();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">Rule Repository</h1>
        <p className="mt-3 text-lg text-gray-600">
          Manage, search, and enforce natural-language rules
        </p>
      </div>

      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <h2 className="text-sm font-medium uppercase tracking-wide text-gray-500">
          Backend Status
        </h2>
        <div className="mt-2 flex items-center gap-2">
          <span
            className={`inline-block h-3 w-3 rounded-full ${
              health?.status === "ok" ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="text-lg font-semibold">
            {health?.status === "ok" ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      <nav className="flex gap-4">
        <a
          href="/rules"
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Browse Rules
        </a>
        <a
          href="/search"
          className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-100"
        >
          Search
        </a>
        <a
          href="/documents"
          className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-100"
        >
          Documents
        </a>
      </nav>
    </main>
  );
}
