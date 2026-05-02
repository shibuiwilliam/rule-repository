"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createProposal } from "@/lib/api";
import { useProject } from "@/lib/project-context";

const PROPOSAL_TYPES = [
  { value: "create", label: "Create", desc: "Propose a new rule" },
  { value: "amend", label: "Amend", desc: "Modify an existing rule" },
  { value: "retire", label: "Retire", desc: "Sunset a rule" },
  { value: "merge", label: "Merge", desc: "Combine overlapping rules" },
  { value: "split", label: "Split", desc: "Break a broad rule into specific ones" },
  { value: "override", label: "Override", desc: "Create a child override in a federation" },
];

export default function NewProposalPage() {
  const router = useRouter();
  const { currentProject } = useProject();
  const [type, setType] = useState("create");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [targetRuleIds, setTargetRuleIds] = useState("");
  const [approvers, setApprovers] = useState("");
  const [statement, setStatement] = useState("");
  const [modality, setModality] = useState("MUST");
  const [severity, setSeverity] = useState("MEDIUM");
  const [scope, setScope] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const changeSpec: Record<string, unknown> = {};
      if (type === "create" || type === "override") {
        changeSpec.new_rule_data = {
          statement,
          modality,
          severity,
          scope: scope ? scope.split(",").map((s: string) => s.trim()) : [],
        };
      }

      const data = {
        proposal_type: type,
        title,
        description,
        target_rule_ids: targetRuleIds ? targetRuleIds.split(",").map((id: string) => id.trim()) : [],
        change_spec: changeSpec,
        required_approvers: approvers ? approvers.split(",").map((a: string) => a.trim()) : [],
      };

      const proposal = await createProposal(data, currentProject?.id);
      router.push(`/proposals/${proposal.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create proposal");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">New Governance Proposal</h1>
        <p className="text-sm text-gray-500 mt-1">
          Propose a rule change for collaborative review and approval.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Proposal Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Type</label>
          <div className="grid grid-cols-3 gap-2">
            {PROPOSAL_TYPES.map((pt) => (
              <button
                key={pt.value}
                type="button"
                onClick={() => setType(pt.value)}
                className={`p-3 rounded-lg border text-left text-sm transition ${
                  type === pt.value
                    ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <span className="font-medium">{pt.label}</span>
                <p className="text-xs text-gray-500 mt-0.5">{pt.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Add input validation requirement for POST endpoints"
            className="w-full border rounded-md px-3 py-2 text-sm"
            required
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Explain the motivation and impact of this change..."
            rows={4}
            className="w-full border rounded-md px-3 py-2 text-sm"
          />
        </div>

        {/* Target Rule IDs (for non-create types) */}
        {type !== "create" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Target Rule IDs (comma-separated)
            </label>
            <input
              type="text"
              value={targetRuleIds}
              onChange={(e) => setTargetRuleIds(e.target.value)}
              placeholder="uuid-1, uuid-2"
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>
        )}

        {/* Rule Details (for create/override) */}
        {(type === "create" || type === "override") && (
          <fieldset className="border rounded-lg p-4 space-y-3">
            <legend className="text-sm font-medium text-gray-700 px-1">New Rule</legend>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Statement</label>
              <textarea
                value={statement}
                onChange={(e) => setStatement(e.target.value)}
                placeholder="All API endpoints MUST validate input..."
                rows={3}
                className="w-full border rounded-md px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Modality</label>
                <select value={modality} onChange={(e) => setModality(e.target.value)} className="w-full border rounded-md px-2 py-1.5 text-sm">
                  {["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"].map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Severity</label>
                <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="w-full border rounded-md px-2 py-1.5 text-sm">
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Scope (comma-sep)</label>
                <input
                  type="text"
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                  placeholder="engineering/api"
                  className="w-full border rounded-md px-2 py-1.5 text-sm"
                />
              </div>
            </div>
          </fieldset>
        )}

        {/* Required Approvers */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Required Approvers (comma-separated user IDs)
          </label>
          <input
            type="text"
            value={approvers}
            onChange={(e) => setApprovers(e.target.value)}
            placeholder="alice, bob"
            className="w-full border rounded-md px-3 py-2 text-sm"
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting || !title}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Creating..." : "Create Proposal"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-md border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
