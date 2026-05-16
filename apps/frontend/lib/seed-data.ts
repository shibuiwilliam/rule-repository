const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * Fetch seed data for a domain from the server.
 * Falls back to empty object on error.
 */
export async function fetchSeedData<T = Record<string, unknown>>(
  domain: string,
  section?: string,
): Promise<T> {
  try {
    const path = section
      ? `/api/v1/seed/${domain}/${section}`
      : `/api/v1/seed/${domain}`;
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) return {} as T;
    return await res.json();
  } catch {
    return {} as T;
  }
}
