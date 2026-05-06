"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createRule } from "@/lib/api";
import { useProject } from "@/lib/project-context";

const MODALITIES = ["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"] as const;
const SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

export default function NewRulePage() {
  const router = useRouter();
  const { currentProject } = useProject();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    statement: "",
    modality: "MUST" as string,
    severity: "MEDIUM" as string,
    scope: "",
    tags: "",
    rationale: "",
    context: "",
    preconditions: "",
    exceptions: "",
    following_examples: "",
    violation_examples: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.statement.trim()) return;

    setSubmitting(true);
    setError("");
    try {
      const rule = await createRule(
        {
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
          context: form.context,
          preconditions: form.preconditions.split("\n").map((s: string) => s.trim()).filter(Boolean),
          exceptions: form.exceptions.split("\n").map((s: string) => s.trim()).filter(Boolean),
          following_examples: form.following_examples.split("\n").map((s: string) => s.trim()).filter(Boolean),
          violation_examples: form.violation_examples.split("\n").map((s: string) => s.trim()).filter(Boolean),
        },
        currentProject?.id,
      );
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
          <label htmlFor="statement" className="block text-sm font-medium text-gray-700" title="The normative statement in natural language -- this is the source of truth">
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
            <label htmlFor="modality" className="block text-sm font-medium text-gray-700" title="Obligation strength: MUST (required), SHOULD (recommended), MAY (optional), INFO (informational)">
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
            <label htmlFor="severity" className="block text-sm font-medium text-gray-700" title="Impact level if violated: LOW, MEDIUM, HIGH, CRITICAL">
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
          <label htmlFor="scope" className="block text-sm font-medium text-gray-700" title="Comma-separated labels for who/what this rule applies to">
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
          <label htmlFor="tags" className="block text-sm font-medium text-gray-700" title="Comma-separated categorization labels for filtering and grouping">
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
          <label htmlFor="rationale" className="block text-sm font-medium text-gray-700" title="Why this rule exists -- helps the LLM evaluator understand intent">
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

        {/* Context */}
        <div>
          <label htmlFor="context" className="block text-sm font-medium text-gray-700" title="Source document context: section hierarchy, regulatory authority, definitions">
            Context
          </label>
          <textarea
            id="context"
            rows={3}
            value={form.context}
            onChange={(e) => setForm({ ...form, context: e.target.value })}
            placeholder="Surrounding document context — section hierarchy, regulatory authority, definitions, or qualifying information that gives this rule meaning."
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
          <p className="mt-1 text-xs text-gray-400">
            Captured automatically during document extraction. For manual rules, describe the source or background.
          </p>
        </div>

        {/* Preconditions */}
        <div>
          <label htmlFor="preconditions" className="block text-sm font-medium text-gray-700" title="When does this rule apply? One condition per line. Leave empty if always applicable">
            Preconditions
          </label>
          <textarea
            id="preconditions"
            rows={3}
            value={form.preconditions}
            onChange={(e) => setForm({ ...form, preconditions: e.target.value })}
            placeholder={"Conditions that must be true for this rule to apply (one per line):\nThe code defines an API endpoint\nThe function handles user input"}
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
          <p className="mt-1 text-xs text-gray-400">One condition per line. Leave empty if the rule applies unconditionally.</p>
        </div>

        {/* Exceptions */}
        <div>
          <label htmlFor="exceptions" className="block text-sm font-medium text-gray-700" title="When does this rule NOT apply? One exception per line">
            Exceptions
          </label>
          <textarea
            id="exceptions"
            rows={2}
            value={form.exceptions}
            onChange={(e) => setForm({ ...form, exceptions: e.target.value })}
            placeholder={"Situations where this rule does NOT apply (one per line):\nInternal-only APIs with no external consumers"}
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
          <p className="mt-1 text-xs text-gray-400">One exception per line. Leave empty if there are no exceptions.</p>
        </div>

        {/* Following Examples */}
        <div>
          <label htmlFor="following_examples" className="block text-sm font-medium text-gray-700" title="Examples of correct behavior from the source document. One per line">
            Following Examples
          </label>
          <textarea
            id="following_examples"
            rows={3}
            value={form.following_examples}
            onChange={(e) => setForm({ ...form, following_examples: e.target.value })}
            placeholder={"Examples of correct behavior (one per line):\nUsing Pydantic BaseModel for request validation\ndef get_user(user_id: int) -> UserResponse:"}
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
          <p className="mt-1 text-xs text-gray-400">Concrete examples of activities that follow this rule. One per line.</p>
        </div>

        {/* Violation Examples */}
        <div>
          <label htmlFor="violation_examples" className="block text-sm font-medium text-gray-700" title="Examples of incorrect behavior from the source document. One per line">
            Violation Examples
          </label>
          <textarea
            id="violation_examples"
            rows={3}
            value={form.violation_examples}
            onChange={(e) => setForm({ ...form, violation_examples: e.target.value })}
            placeholder={"Examples of incorrect behavior (one per line):\nAccepting raw dict without validation\ndef get_user(id):  # missing type hints"}
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
          <p className="mt-1 text-xs text-gray-400">Concrete examples of activities that violate this rule. One per line.</p>
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
            title="Save this rule and add it to the current project"
          >
            {submitting ? "Creating..." : "Create Rule"}
          </button>
        </div>
      </form>
    </div>
  );
}
