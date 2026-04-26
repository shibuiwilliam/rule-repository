"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createRule } from "@/lib/api";

const MODALITIES = ["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"] as const;
const SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

export default function NewRulePage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    statement: "",
    modality: "MUST" as string,
    severity: "MEDIUM" as string,
    scope: "",
    tags: "",
    rationale: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.statement.trim()) return;

    setSubmitting(true);
    setError("");
    try {
      const rule = await createRule({
        statement: form.statement,
        modality: form.modality,
        severity: form.severity,
        scope: form.scope
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        tags: form.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        rationale: form.rationale,
      });
      router.push(`/rules/${rule.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create rule");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">Create New Rule</h1>

      {error && (
        <p className="mb-4 rounded bg-red-50 px-4 py-2 text-sm text-red-800">{error}</p>
      )}

      <form onSubmit={handleSubmit} className="space-y-6 rounded-lg border bg-white p-6">
        {/* Statement */}
        <div>
          <label htmlFor="statement" className="block text-sm font-medium text-gray-700">
            Rule Statement *
          </label>
          <textarea
            id="statement"
            rows={4}
            required
            value={form.statement}
            onChange={(e) => setForm({ ...form, statement: e.target.value })}
            placeholder="Enter the rule as a natural-language normative statement..."
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Modality + Severity */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="modality" className="block text-sm font-medium text-gray-700">
              Modality
            </label>
            <select
              id="modality"
              value={form.modality}
              onChange={(e) => setForm({ ...form, modality: e.target.value })}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            >
              {MODALITIES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="severity" className="block text-sm font-medium text-gray-700">
              Severity
            </label>
            <select
              id="severity"
              value={form.severity}
              onChange={(e) => setForm({ ...form, severity: e.target.value })}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Scope */}
        <div>
          <label htmlFor="scope" className="block text-sm font-medium text-gray-700">
            Scope
          </label>
          <input
            id="scope"
            type="text"
            value={form.scope}
            onChange={(e) => setForm({ ...form, scope: e.target.value })}
            placeholder="e.g. engineering, hr/attendance (comma-separated)"
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        {/* Tags */}
        <div>
          <label htmlFor="tags" className="block text-sm font-medium text-gray-700">
            Tags
          </label>
          <input
            id="tags"
            type="text"
            value={form.tags}
            onChange={(e) => setForm({ ...form, tags: e.target.value })}
            placeholder="e.g. code-review, deployment, policy (comma-separated)"
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        {/* Rationale */}
        <div>
          <label htmlFor="rationale" className="block text-sm font-medium text-gray-700">
            Rationale
          </label>
          <textarea
            id="rationale"
            rows={2}
            value={form.rationale}
            onChange={(e) => setForm({ ...form, rationale: e.target.value })}
            placeholder="Why does this rule exist?"
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !form.statement.trim()}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Creating..." : "Create Rule"}
          </button>
        </div>
      </form>
    </div>
  );
}
