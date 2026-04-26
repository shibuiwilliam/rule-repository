"use client";

import { useState } from "react";
import Link from "next/link";
import type { SearchResult } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type SearchMode = "fulltext" | "vector" | "hybrid";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/search/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, page: 1, page_size: 20 }),
      });
      if (!res.ok) throw new Error(`Search failed: ${res.status}`);
      setResults(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Search Rules</h1>

      <form onSubmit={handleSearch} className="mb-8 space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for rules..."
            className="flex-1 rounded-md border px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as SearchMode)}
            className="rounded-md border px-3 py-2 text-sm"
          >
            <option value="hybrid">Hybrid</option>
            <option value="fulltext">Full-text</option>
            <option value="vector">Semantic</option>
          </select>
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </form>

      {error && <p className="mb-4 text-red-600">{error}</p>}

      {results && (
        <div>
          <p className="mb-4 text-sm text-gray-600">
            {results.total} result{results.total !== 1 ? "s" : ""} for &ldquo;
            {results.query}&rdquo;
          </p>
          <div className="space-y-4">
            {results.items.map((item) => (
              <div
                key={item.rule.id}
                className="rounded-lg border bg-white p-4 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <Link
                    href={`/rules/${item.rule.id}`}
                    className="text-sm font-medium text-blue-600 hover:underline"
                  >
                    {item.rule.statement.length > 200
                      ? `${item.rule.statement.slice(0, 200)}...`
                      : item.rule.statement}
                  </Link>
                  <span className="ml-2 text-xs text-gray-400">
                    score: {item.score.toFixed(3)}
                  </span>
                </div>
                <div className="mt-2 flex gap-2">
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800">
                    {item.rule.modality}
                  </span>
                  <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs text-orange-800">
                    {item.rule.severity}
                  </span>
                  {item.rule.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
