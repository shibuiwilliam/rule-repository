"use client";

/**
 * Inline edit form for an existing rule. Renders as a modal overlay.
 */

import { useState } from "react";
import { updateRule } from "@/lib/api";
import type { Rule } from "@/lib/api";

const MODALITIES = ["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"] as const;
const SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
const STATUSES = ["DRAFT", "REVIEW", "APPROVED", "EFFECTIVE", "SUPERSEDED", "RETIRED"] as const;

interface RuleEditFormProps {
  rule: Rule;
  onSaved: () => void;
  onCancel: () => void;
}

export default function RuleEditForm({ rule, onSaved, onCancel }: RuleEditFormProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    statement: rule.statement,
    modality: rule.modality,
    severity: rule.severity,
    status: rule.status,
    rationale: rule.rationale,
    context: rule.context || "",
    preconditions: (rule.preconditions || []).join("\n"),
    exceptions: (rule.exceptions || []).join("\n"),
    following_examples: (rule.following_examples || []).join("\n"),
    violation_examples: (rule.violation_examples || []).join("\n"),
    scope: rule.scope.join(", "),
    tags: rule.tags.join(", "),
    revision_note: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await updateRule(rule.id, {
        statement: form.statement,
        modality: form.modality,
        severity: form.severity,
        status: form.status,
        rationale: form.rationale,
        context: form.context,
        scope: form.scope
          .split(",")
          .map((s: string) => s.trim())
          .filter(Boolean),
        tags: form.tags
          .split(",")
          .map((t: string) => t.trim())
          .filter(Boolean),
        preconditions: form.preconditions.split("\n").map((s: string) => s.trim()).filter(Boolean),
        exceptions: form.exceptions.split("\n").map((s: string) => s.trim()).filter(Boolean),
        following_examples: form.following_examples.split("\n").map((s: string) => s.trim()).filter(Boolean),
        violation_examples: form.violation_examples.split("\n").map((s: string) => s.trim()).filter(Boolean),
        revision_note: form.revision_note,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update rule");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-bold">Edit Rule</h2>

        {error && (
          <p className="mb-3 rounded bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Statement</label>
            <textarea
              rows={3}
              value={form.statement}
              onChange={(e) => setForm({ ...form, statement: e.target.value })}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">Modality</label>
              <select
                value={form.modality}
                onChange={(e) => setForm({ ...form, modality: e.target.value })}
                className="mt-1 w-full rounded-md border px-2 py-1.5 text-sm"
              >
                {MODALITIES.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Severity</label>
              <select
                value={form.severity}
                onChange={(e) => setForm({ ...form, severity: e.target.value })}
                className="mt-1 w-full rounded-md border px-2 py-1.5 text-sm"
              >
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Status</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className="mt-1 w-full rounded-md border px-2 py-1.5 text-sm"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">Scope</label>
              <input
                value={form.scope}
                onChange={(e) => setForm({ ...form, scope: e.target.value })}
                placeholder="comma-separated"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Tags</label>
              <input
                value={form.tags}
                onChange={(e) => setForm({ ...form, tags: e.target.value })}
                placeholder="comma-separated"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Rationale</label>
            <textarea
              rows={2}
              value={form.rationale}
              onChange={(e) => setForm({ ...form, rationale: e.target.value })}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Context</label>
            <textarea
              rows={3}
              value={form.context}
              onChange={(e) => setForm({ ...form, context: e.target.value })}
              placeholder="Surrounding document context — section hierarchy, regulatory authority, definitions."
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Preconditions</label>
            <textarea
              rows={3}
              value={form.preconditions}
              onChange={(e) => setForm({ ...form, preconditions: e.target.value })}
              placeholder="Conditions that must be true for this rule to apply (one per line)"
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Exceptions</label>
            <textarea
              rows={2}
              value={form.exceptions}
              onChange={(e) => setForm({ ...form, exceptions: e.target.value })}
              placeholder="Situations where this rule does NOT apply (one per line)"
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Following Examples</label>
            <textarea
              rows={2}
              value={form.following_examples}
              onChange={(e) => setForm({ ...form, following_examples: e.target.value })}
              placeholder="Examples of correct behavior (one per line)"
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Violation Examples</label>
            <textarea
              rows={2}
              value={form.violation_examples}
              onChange={(e) => setForm({ ...form, violation_examples: e.target.value })}
              placeholder="Examples of incorrect behavior (one per line)"
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Revision Note *
            </label>
            <input
              required
              value={form.revision_note}
              onChange={(e) => setForm({ ...form, revision_note: e.target.value })}
              placeholder="Why are you making this change?"
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onCancel}
              className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !form.revision_note.trim()}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
