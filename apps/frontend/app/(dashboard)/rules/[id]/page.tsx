import Link from "next/link";
import { getRule, getRevisions, getRelationships, getGraph } from "@/lib/api";
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
                  ? rule.tags.map((t) => (
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
              {relationships.map((rel, i) => (
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
            {revisions.map((rev) => (
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
