import Link from "next/link";
import { getRule, getRevisions, getRelationships, getGraph, getDocument } from "@/lib/api";
import type { DocumentInfo, Relationship, Revision } from "@/lib/api";
import Badge from "@/components/Badge";
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
          <h2 className="mb-3 text-sm font-medium uppercase text-gray-500">
            Relationships ({relationships.length})
          </h2>
          {relationships.length === 0 ? (
            <p className="text-sm text-gray-500">No relationships.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {relationships.map((rel: Relationship, i: number) => (
                <li key={i} className="flex items-center gap-2">
                  <Badge label={rel.relationship_type} variant="relationship" />
                  <Link
                    href={`/rules/${rel.source_id === id ? rel.target_id : rel.source_id}`}
                    className="font-mono text-xs text-blue-600 hover:underline"
                  >
                    {(rel.source_id === id ? rel.target_id : rel.source_id).slice(0, 8)}...
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

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
