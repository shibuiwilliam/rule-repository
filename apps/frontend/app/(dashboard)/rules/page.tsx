"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { type RuleList, getRules } from "@/lib/api";
import { useProject } from "@/lib/project-context";

const MODALITY_COLORS: Record<string, string> = {
  MUST: "bg-red-100 text-red-800",
  MUST_NOT: "bg-red-200 text-red-900",
  SHOULD: "bg-yellow-100 text-yellow-800",
  MAY: "bg-green-100 text-green-800",
  INFO: "bg-blue-100 text-blue-800",
};

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH: "bg-orange-500 text-white",
  MEDIUM: "bg-yellow-500 text-white",
  LOW: "bg-gray-400 text-white",
};

export default function RulesPage() {
  const { currentProject } = useProject();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<RuleList | null>(null);
  const [loading, setLoading] = useState(true);

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getRules(page, 20, currentProject?.id);
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [page, currentProject?.id]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  // Reset to page 1 when project changes
  useEffect(() => {
    setPage(1);
  }, [currentProject?.id]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Rules</h1>
        <Link
          href="/rules/new"
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          New Rule
        </Link>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-lg border bg-gray-100" />
          ))}
        </div>
      ) : !data ? (
        <p className="text-gray-500">
          Unable to connect to the backend. Is the server running?
        </p>
      ) : data.items.length === 0 ? (
        <p className="text-gray-500">No rules found in this project. Create your first rule.</p>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Statement
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Modality
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Severity
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Tags
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {data.items.map((rule) => (
                  <tr key={rule.id} className="hover:bg-gray-50">
                    <td className="max-w-md px-4 py-3">
                      <Link
                        href={`/rules/${rule.id}`}
                        className="text-sm text-blue-600 hover:underline"
                      >
                        {rule.statement.length > 120
                          ? `${rule.statement.slice(0, 120)}...`
                          : rule.statement}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${MODALITY_COLORS[rule.modality] ?? "bg-gray-100"}`}
                      >
                        {rule.modality}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_COLORS[rule.severity] ?? "bg-gray-300"}`}
                      >
                        {rule.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {rule.status}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {rule.tags.map((tag) => (
                          <span
                            key={tag}
                            className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data.total > data.page_size && (
            <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
              <span>
                Showing {(page - 1) * data.page_size + 1}–
                {Math.min(page * data.page_size, data.total)} of {data.total}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded border px-3 py-1 hover:bg-gray-100 disabled:opacity-40"
                >
                  Previous
                </button>
                <span className="px-2 py-1 text-gray-400">
                  {page} / {Math.ceil(data.total / data.page_size)}
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * data.page_size >= data.total}
                  className="rounded border px-3 py-1 hover:bg-gray-100 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
