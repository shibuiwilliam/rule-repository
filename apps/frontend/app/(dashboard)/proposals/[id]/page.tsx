"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  type Proposal,
  type ProposalComment,
  getProposal,
  submitProposal,
  voteOnProposal,
  enactProposal,
  revertProposal,
  closeProposal,
  addProposalComment,
  refreshProposalAnalysis,
} from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  review: "bg-blue-100 text-blue-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  enacted: "bg-purple-100 text-purple-700",
  reverted: "bg-orange-100 text-orange-700",
  closed: "bg-gray-200 text-gray-500",
};

export default function ProposalDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [commentBody, setCommentBody] = useState("");
  const [voterId, setVoterId] = useState("reviewer");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await getProposal(id);
      setProposal(data);
    } catch {
      setError("Proposal not found");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const doAction = async (action: () => Promise<Proposal>) => {
    setActing(true);
    setError("");
    try {
      const updated = await action();
      setProposal(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActing(false);
    }
  };

  const handleComment = async () => {
    if (!commentBody.trim()) return;
    setActing(true);
    try {
      await addProposalComment(id, { body: commentBody });
      setCommentBody("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add comment");
    } finally {
      setActing(false);
    }
  };

  if (loading) return <div className="animate-pulse h-64 bg-gray-100 rounded-lg" />;
  if (!proposal) return <div className="text-center py-12 text-gray-500">{error || "Not found"}</div>;

  const approveCount = proposal.approval_votes.filter((v: { vote: string }) => v.vote === "approve" || v.vote === "conditional").length;
  const rejectCount = proposal.approval_votes.filter((v: { vote: string }) => v.vote === "reject").length;

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link href="/proposals" className="text-sm text-gray-400 hover:text-gray-600">&larr; Proposals</Link>
          </div>
          <h1 className="text-2xl font-bold">{proposal.title}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[proposal.status]}`}>
              {proposal.status}
            </span>
            <span className="text-xs text-gray-400 bg-gray-50 rounded px-1.5 py-0.5">{proposal.proposal_type}</span>
            <span className="text-xs text-gray-400">by {proposal.author_id}</span>
            <span className="text-xs text-gray-400">{new Date(proposal.created_at).toLocaleString()}</span>
          </div>
        </div>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">{error}</div>}

      {/* Actions Bar */}
      <div className="flex gap-2 flex-wrap">
        {proposal.status === "draft" && (
          <button onClick={() => doAction(() => submitProposal(id))} disabled={acting}
            title="Submit this proposal for review — runs conflict analysis and notifies approvers"
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            Submit for Review
          </button>
        )}
        {proposal.status === "review" && (
          <>
            <div className="flex items-center gap-1">
              <input type="text" value={voterId} onChange={(e) => setVoterId(e.target.value)}
                className="border rounded px-2 py-1 text-xs w-24" placeholder="your ID" />
              <button onClick={() => doAction(() => voteOnProposal(id, "approve", voterId))} disabled={acting}
                title="Cast an approval vote on this proposal"
                className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
                Approve
              </button>
              <button onClick={() => doAction(() => voteOnProposal(id, "reject", voterId))} disabled={acting}
                title="Reject this proposal — it can be returned to draft for revision"
                className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">
                Reject
              </button>
            </div>
          </>
        )}
        {proposal.status === "approved" && (
          <button onClick={() => doAction(() => enactProposal(id))} disabled={acting}
            title="Apply the approved changes to the rule corpus"
            className="rounded-md bg-purple-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">
            Enact Changes
          </button>
        )}
        {proposal.status === "enacted" && (
          <button onClick={() => doAction(() => revertProposal(id))} disabled={acting}
            className="rounded-md bg-orange-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-orange-700 disabled:opacity-50">
            Revert
          </button>
        )}
        {!["enacted", "closed"].includes(proposal.status) && (
          <button onClick={() => doAction(() => closeProposal(id))} disabled={acting}
            className="rounded-md border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">
            Close
          </button>
        )}
        <button onClick={() => doAction(() => refreshProposalAnalysis(id))} disabled={acting}
          title="Re-run conflict detection and impact preview"
          className="rounded-md border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">
          Refresh Analysis
        </button>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          {proposal.description && (
            <section className="border rounded-lg p-4">
              <h2 className="text-sm font-semibold text-gray-700 mb-2" title="Detailed motivation and context for the proposed change">Description</h2>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{proposal.description}</p>
            </section>
          )}

          {/* Change Spec */}
          {Object.keys(proposal.change_spec).length > 0 && (
            <section className="border rounded-lg p-4">
              <h2 className="text-sm font-semibold text-gray-700 mb-2" title="Structured specification of what will change">Proposed Changes</h2>
              <pre className="text-xs bg-gray-50 rounded p-3 overflow-x-auto">
                {JSON.stringify(proposal.change_spec, null, 2)}
              </pre>
            </section>
          )}

          {/* Comments */}
          <section className="border rounded-lg p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3" title="Threaded discussion with inline suggestions">
              Comments ({proposal.comments.length})
            </h2>
            {proposal.comments.length > 0 ? (
              <div className="space-y-3 mb-4">
                {proposal.comments.map((c: ProposalComment) => (
                  <div key={c.id} className="border-l-2 border-gray-200 pl-3">
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      <span className="font-medium text-gray-600">{c.author_id}</span>
                      <span>{new Date(c.created_at).toLocaleString()}</span>
                      {c.comment_type !== "comment" && (
                        <span className="bg-yellow-50 text-yellow-700 rounded px-1.5 py-0.5">{c.comment_type}</span>
                      )}
                      {c.resolved && <span className="text-green-600">Resolved</span>}
                    </div>
                    <p className="text-sm text-gray-700 mt-1">{c.body}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 mb-4">No comments yet.</p>
            )}

            {/* Add Comment */}
            <div className="flex gap-2">
              <input
                type="text"
                value={commentBody}
                onChange={(e) => setCommentBody(e.target.value)}
                placeholder="Add a comment..."
                className="flex-1 border rounded-md px-3 py-1.5 text-sm"
                onKeyDown={(e) => e.key === "Enter" && handleComment()}
              />
              <button
                onClick={handleComment}
                disabled={acting || !commentBody.trim()}
                className="rounded-md bg-gray-800 px-3 py-1.5 text-sm text-white hover:bg-gray-900 disabled:opacity-50"
              >
                Comment
              </button>
            </div>
          </section>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Approval Status */}
          <section className="border rounded-lg p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-2" title="Required approvers and their vote status">Approvals</h2>
            {proposal.required_approvers.length > 0 ? (
              <div className="space-y-1.5">
                {proposal.required_approvers.map((a: string) => {
                  const vote = proposal.approval_votes.find((v: { user_id: string }) => v.user_id === a);
                  return (
                    <div key={a} className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">{a}</span>
                      {vote ? (
                        <span className={`text-xs rounded px-1.5 py-0.5 ${
                          vote.vote === "approve" ? "bg-green-100 text-green-700"
                            : vote.vote === "reject" ? "bg-red-100 text-red-700"
                              : "bg-yellow-100 text-yellow-700"
                        }`}>{vote.vote}</span>
                      ) : (
                        <span className="text-xs text-gray-400">pending</span>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-gray-400">No approvers required.</p>
            )}
            <div className="mt-2 text-xs text-gray-400">
              {approveCount} approved, {rejectCount} rejected
            </div>
          </section>

          {/* Target Rules */}
          {proposal.target_rule_ids.length > 0 && (
            <section className="border rounded-lg p-4">
              <h2 className="text-sm font-semibold text-gray-700 mb-2">Target Rules</h2>
              <div className="space-y-1">
                {proposal.target_rule_ids.map((rid: string) => (
                  <Link key={rid} href={`/rules/${rid}`} className="block text-xs text-blue-600 hover:underline truncate">
                    {rid}
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Conflict Analysis */}
          {proposal.conflict_analysis && (
            <section className="border rounded-lg p-4">
              <h2 className="text-sm font-semibold text-gray-700 mb-2" title="Automatically detected conflicts with existing rules">Conflict Analysis</h2>
              <p className="text-sm">
                <span className={`font-medium ${(proposal.conflict_analysis.conflicts_found as number) > 0 ? "text-orange-600" : "text-green-600"}`}>
                  {proposal.conflict_analysis.conflicts_found as number} conflict(s) found
                </span>
              </p>
              {Array.isArray(proposal.conflict_analysis.conflicts) && (proposal.conflict_analysis.conflicts as Array<Record<string, unknown>>).length > 0 && (
                <div className="mt-2 space-y-1.5">
                  {(proposal.conflict_analysis.conflicts as Array<{ rule_id: string; statement: string; overlap_type: string }>).map((c: { rule_id: string; statement: string; overlap_type: string }, i: number) => (
                    <div key={i} className="text-xs bg-orange-50 rounded p-2">
                      <p className="text-orange-700">{c.overlap_type}</p>
                      <p className="text-gray-600 truncate">{c.statement}</p>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Impact Preview */}
          {proposal.impact_preview && (
            <section className="border rounded-lg p-4">
              <h2 className="text-sm font-semibold text-gray-700 mb-2" title="Estimated effect on existing evaluations if this proposal is enacted">Impact Preview</h2>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Affected rules</span>
                  <span className="font-medium">{proposal.impact_preview.affected_rules as number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Evaluations affected</span>
                  <span className="font-medium">{proposal.impact_preview.total_evaluations_affected as number}</span>
                </div>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
