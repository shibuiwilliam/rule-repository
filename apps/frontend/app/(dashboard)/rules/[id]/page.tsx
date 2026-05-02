import Link from "next/link";
import { getRule, getRevisions, getRelationships, getGraph, getDocument } from "@/lib/api";
import type { DocumentInfo, Revision } from "@/lib/api";

const API_BASE =
  process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface EffectivenessData {
  effectiveness_score: number;
  precision: number;
  prevention_rate: number;
  agent_adoption: number;
  total_evaluations: number;
  true_positives: number;
  false_positives: number;
}
import Badge from "@/components/Badge";
import RelationshipManager from "@/components/RelationshipManager";
import RuleDetailClient from "./client";

export default async function RuleDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let rule, revisions, relationships, graph;
  try {
    [rule, revisions, relationships, graph] = await Promise.all([
      getRule(id),
      getRevisions(id),
      getRelationships(id),
      getGraph(id, 2),
    ]);
  } catch {
    return (
      <div className="text-red-600">
        Failed to load rule.{" "}
        <Link href="/rules" className="underline">
          Back to rules
        </Link>
      </div>
    );
  }

  // Fetch effectiveness score
  let effectiveness: EffectivenessData | null = null;
  try {
    const effRes = await fetch(
      `${API_BASE}/api/v1/intelligence/effectiveness/${id}`,
      { cache: "no-store" },
    );
    if (effRes.ok) effectiveness = await effRes.json();
  } catch {
    // Non-critical — page still renders without effectiveness
  }

  // Resolve source document filenames
  const sourceDocMap: Record<string, DocumentInfo> = {};
  if (rule.source_refs && rule.source_refs.length > 0) {
    const docIds: string[] = [
      ...new Set(
        rule.source_refs
          .map((ref: Record<string, unknown>) => ref.document_id as string)
          .filter(Boolean),
      ),
    ];
    const docs = await Promise.all(
      docIds.map((docId: string) => getDocument(docId).catch(() => null)),
    );
    for (const doc of docs) {
      if (doc) sourceDocMap[doc.id] = doc;
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link href="/rules" className="text-sm text-gray-500 hover:underline">
            &larr; Back to rules
          </Link>
          <h1 className="mt-2 text-2xl font-bold">{rule.statement}</h1>
        </div>
        <div className="flex items-center gap-2">
          <Badge label={rule.modality} variant="modality" />
          <Badge label={rule.severity} variant="severity" />
          <Badge label={rule.status} variant="status" />
          <RuleDetailClient rule={rule} />
        </div>
      </div>

      {/* Metadata + Relationships side by side */}
      <div className="grid grid-cols-2 gap-6">
        <div className="rounded-lg border bg-white p-4">
          <h2 className="mb-3 text-sm font-medium uppercase text-gray-500">Details</h2>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="font-medium text-gray-600">Rationale</dt>
              <dd className="text-gray-900">{rule.rationale || "—"}</dd>
            </div>
            {rule.context && (
              <div>
                <dt className="font-medium text-gray-600">Context</dt>
                <dd className="text-gray-900 whitespace-pre-wrap">{rule.context}</dd>
              </div>
            )}
            {rule.preconditions && rule.preconditions.length > 0 && (
              <div>
                <dt className="font-medium text-gray-600">Preconditions</dt>
                <dd>
                  <ul className="list-disc list-inside text-gray-900 text-sm">
                    {rule.preconditions.map((p: string, i: number) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            )}
            {rule.exceptions && rule.exceptions.length > 0 && (
              <div>
                <dt className="font-medium text-gray-600">Exceptions</dt>
                <dd>
                  <ul className="list-disc list-inside text-gray-900 text-sm">
                    {rule.exceptions.map((e: string, i: number) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            )}
            {rule.following_examples && rule.following_examples.length > 0 && (
              <div>
                <dt className="font-medium text-gray-600">Following Examples</dt>
                <dd>
                  <ul className="space-y-1 text-sm">
                    {rule.following_examples.map((ex: string, i: number) => (
                      <li key={i} className="rounded bg-green-50 px-2 py-1 text-green-800">{ex}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            )}
            {rule.violation_examples && rule.violation_examples.length > 0 && (
              <div>
                <dt className="font-medium text-gray-600">Violation Examples</dt>
                <dd>
                  <ul className="space-y-1 text-sm">
                    {rule.violation_examples.map((ex: string, i: number) => (
                      <li key={i} className="rounded bg-red-50 px-2 py-1 text-red-800">{ex}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            )}
            <div>
              <dt className="font-medium text-gray-600">Scope</dt>
              <dd>{rule.scope.length ? rule.scope.join(", ") : "—"}</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-600">Tags</dt>
              <dd>
                {rule.tags.length
                  ? rule.tags.map((t: string) => (
                      <Badge key={t} label={t} variant="tag" className="mr-1" />
                    ))
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-gray-600">Owner</dt>
              <dd>{rule.governance?.owner ?? "—"}</dd>
            </div>
            <div>
              <dt className="font-medium text-gray-600">Effective Period</dt>
              <dd>
                {rule.effective_period?.valid_from ?? "—"} to{" "}
                {rule.effective_period?.valid_until ?? "ongoing"}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-gray-600">Source Documents</dt>
              <dd>
                {rule.source_refs && rule.source_refs.length > 0 ? (
                  <ul className="space-y-2">
                    {rule.source_refs.map((ref: Record<string, unknown>, i: number) => {
                      const docId = String(ref.document_id ?? "");
                      const doc = sourceDocMap[docId];
                      return (
                        <li key={i} className="flex items-center gap-2 rounded-md bg-gray-50 px-3 py-2">
                          <svg className="h-4 w-4 flex-shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-gray-900">
                              {doc ? doc.filename : `${docId.slice(0, 8)}...`}
                            </p>
                            <p className="text-xs text-gray-500">
                              {doc && (
                                <span>{doc.mime_type} &middot; {(doc.size_bytes / 1024).toFixed(1)} KB</span>
                              )}
                              {ref.section ? (
                                <span> &middot; &sect; {String(ref.section)}</span>
                              ) : null}
                              {ref.page != null && (
                                <span> &middot; p.{String(ref.page)}</span>
                              )}
                              {!doc && docId && (
                                <span className="font-mono">{docId}</span>
                              )}
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-gray-600">ID</dt>
              <dd className="font-mono text-xs text-gray-500">{rule.id}</dd>
            </div>
          </dl>
        </div>

        <div className="rounded-lg border bg-white p-4">
          <RelationshipManager ruleId={id} relationships={relationships} />
        </div>
      </div>

      {/* Effectiveness */}
      {effectiveness && effectiveness.total_evaluations > 0 && (
        <div className="rounded-lg border bg-white p-5">
          <h2 className="mb-3 text-sm font-medium uppercase text-gray-500">
            Effectiveness
          </h2>
          <div className="flex items-center gap-8">
            <div className="text-center">
              <span
                className={`text-4xl font-bold ${
                  effectiveness.effectiveness_score >= 70
                    ? "text-green-600"
                    : effectiveness.effectiveness_score >= 40
                      ? "text-yellow-600"
                      : "text-red-600"
                }`}
              >
                {Math.round(effectiveness.effectiveness_score)}
              </span>
              <p className="mt-1 text-xs text-gray-400">Score</p>
            </div>
            <div className="flex-1 space-y-2.5">
              <EffectivenessBar label="Precision" value={effectiveness.precision} />
              <EffectivenessBar label="Prevention" value={effectiveness.prevention_rate} />
              <EffectivenessBar label="Agent Adoption" value={effectiveness.agent_adoption} />
            </div>
          </div>
          <p className="mt-3 text-xs text-gray-400">
            {effectiveness.total_evaluations} evaluations |{" "}
            {effectiveness.true_positives} true positives |{" "}
            {effectiveness.false_positives} false positives
          </p>
        </div>
      )}

      {/* Relationship Graph */}
      {(graph.nodes.length > 0 || graph.edges.length > 0) && (
        <div className="rounded-lg border bg-white p-4">
          <h2 className="mb-3 text-sm font-medium uppercase text-gray-500">
            Relationship Graph
          </h2>
          <RuleDetailClient rule={rule} graph={graph} showGraph />
        </div>
      )}

      {/* Revisions */}
      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 text-sm font-medium uppercase text-gray-500">
          Revision History ({revisions.length})
        </h2>
        {revisions.length === 0 ? (
          <p className="text-sm text-gray-500">No revisions.</p>
        ) : (
          <div className="space-y-3">
            {revisions.map((rev: Revision) => (
              <div key={rev.id} className="border-l-2 border-gray-200 pl-4">
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-medium">Rev #{rev.revision_number}</span>
                  <span className="text-gray-500">by {rev.changed_by}</span>
                  <span className="text-gray-400">
                    {new Date(rev.created_at).toLocaleString()}
                  </span>
                </div>
                {rev.change_note && (
                  <p className="mt-1 text-sm text-gray-600">{rev.change_note}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EffectivenessBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <span className="w-28 text-xs text-gray-500">{label}</span>
      <div className="h-2 flex-1 rounded-full bg-gray-100">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-right text-xs text-gray-500">{pct}%</span>
    </div>
  );
}
