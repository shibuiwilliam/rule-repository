"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { type Proposal, getProposals } from "@/lib/api";
import { useProject } from "@/lib/project-context";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  review: "bg-blue-100 text-blue-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  enacted: "bg-purple-100 text-purple-700",
  reverted: "bg-orange-100 text-orange-700",
  closed: "bg-gray-200 text-gray-500",
};

const TYPE_LABELS: Record<string, string> = {
  create: "Create",
  amend: "Amend",
  retire: "Retire",
  merge: "Merge",
  split: "Split",
  override: "Override",
};

const STATUS_TITLES: Record<string, string> = {
  "": "Show proposals in any status",
  draft: "Proposals still being edited before submission",
  review: "Proposals awaiting approver votes",
  approved: "Proposals that received sufficient approvals",
  enacted: "Proposals whose changes have been applied",
  rejected: "Proposals that were rejected by approvers",
  closed: "Proposals that were closed without enactment",
};

export default function ProposalsPage() {
  const { currentProject } = useProject();
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const loadProposals = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getProposals(
        statusFilter || undefined,
        page,
        20,
        currentProject?.id,
      );
      setProposals(data.items);
      setTotal(data.total);
    } catch {
      setProposals([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page, currentProject?.id]);

  useEffect(() => {
    loadProposals();
  }, [loadProposals]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" title="Governance proposals for collaborative rule changes with multi-approver voting">Governance Proposals</h1>
          <p className="text-sm text-gray-500 mt-1">
            Propose, review, and approve rule changes through a collaborative workflow.
          </p>
        </div>
        <Link
          href="/proposals/new"
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          title="Create a new proposal to add, modify, retire, merge, or split rules"
        >
          New Proposal
        </Link>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex gap-2 border-b pb-2">
        {["", "draft", "review", "approved", "enacted", "rejected", "closed"].map((s) => (
          <button
            key={s}
            onClick={() => { setStatusFilter(s); setPage(1); }}
            title={STATUS_TITLES[s] ?? ""}
            className={`px-3 py-1.5 text-sm rounded-t-md ${
              statusFilter === s
                ? "bg-blue-50 text-blue-700 border-b-2 border-blue-600 font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {s ? s.charAt(0).toUpperCase() + s.slice(1) : "All"}
          </button>
        ))}
      </div>

      {/* Proposal List */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : proposals.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg">No proposals found</p>
          <p className="text-sm mt-1">Create your first proposal to start the governance workflow.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {proposals.map((p: Proposal) => (
            <Link
              key={p.id}
              href={`/proposals/${p.id}`}
              className="block border rounded-lg p-4 hover:border-blue-300 hover:bg-blue-50/30 transition"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[p.status] || "bg-gray-100"}`}>
                      {p.status}
                    </span>
                    <span className="text-xs text-gray-400 bg-gray-50 rounded px-1.5 py-0.5">
                      {TYPE_LABELS[p.proposal_type] || p.proposal_type}
                    </span>
                    <h3 className="text-sm font-semibold truncate">{p.title}</h3>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 truncate">
                    by {p.author_id} &middot; {new Date(p.created_at).toLocaleDateString()}
                    {p.target_rule_ids.length > 0 && ` \u00b7 ${p.target_rule_ids.length} rule(s)`}
                  </p>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-400 ml-4 shrink-0">
                  {p.approval_votes.length > 0 && (
                    <span>{p.approval_votes.filter((v: { vote: string }) => v.vote === "approve").length}/{p.required_approvers.length} approved</span>
                  )}
                  {p.comments.length > 0 && (
                    <span>{p.comments.length} comments</span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            className="px-3 py-1 text-sm border rounded disabled:opacity-40"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-sm text-gray-500">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <button
            disabled={page >= Math.ceil(total / 20)}
            onClick={() => setPage(page + 1)}
            className="px-3 py-1 text-sm border rounded disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
