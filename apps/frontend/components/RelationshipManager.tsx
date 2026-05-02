"use client";

import { useState } from "react";
import Link from "next/link";
import { createRelationship, deleteRelationship } from "@/lib/api";
import type { Relationship } from "@/lib/api";

const RELATIONSHIP_TYPES = [
  { value: "REFINES", label: "Refines", desc: "This rule adds detail to the target rule" },
  { value: "OVERRIDES", label: "Overrides", desc: "This rule supersedes the target rule" },
  { value: "CONFLICTS_WITH", label: "Conflicts with", desc: "This rule contradicts the target rule" },
  { value: "DEPENDS_ON", label: "Depends on", desc: "This rule requires the target rule to be satisfied first" },
  { value: "DERIVES_FROM", label: "Derives from", desc: "This rule was created from the target rule" },
  { value: "SUCCEEDS", label: "Succeeds", desc: "This rule replaces the target rule" },
];

const TYPE_COLORS: Record<string, string> = {
  REFINES: "bg-blue-100 text-blue-700",
  OVERRIDES: "bg-red-100 text-red-700",
  CONFLICTS_WITH: "bg-orange-100 text-orange-700",
  DEPENDS_ON: "bg-purple-100 text-purple-700",
  DERIVES_FROM: "bg-cyan-100 text-cyan-700",
  SUCCEEDS: "bg-green-100 text-green-700",
};

interface RelationshipManagerProps {
  ruleId: string;
  relationships: Relationship[];
}

export default function RelationshipManager({ ruleId, relationships: initial }: RelationshipManagerProps) {
  const [relationships, setRelationships] = useState<Relationship[]>(initial);
  const [showForm, setShowForm] = useState(false);
  const [targetId, setTargetId] = useState("");
  const [relType, setRelType] = useState("DEPENDS_ON");
  const [direction, setDirection] = useState<"outgoing" | "incoming">("outgoing");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    if (!targetId.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const rel = await createRelationship({
        source_id: direction === "outgoing" ? ruleId : targetId.trim(),
        target_id: direction === "outgoing" ? targetId.trim() : ruleId,
        relationship_type: relType,
      });
      setRelationships([...relationships, rel]);
      setTargetId("");
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create relationship");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (rel: Relationship) => {
    try {
      await deleteRelationship(String(rel.source_id), String(rel.target_id), rel.relationship_type);
      setRelationships(relationships.filter((r) =>
        !(String(r.source_id) === String(rel.source_id) &&
          String(r.target_id) === String(rel.target_id) &&
          r.relationship_type === rel.relationship_type)
      ));
    } catch {
      window.location.reload();
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium uppercase text-gray-500">
          Relationships ({relationships.length})
        </h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-xs text-blue-600 hover:text-blue-700"
        >
          {showForm ? "Cancel" : "+ Add"}
        </button>
      </div>

      {/* Create relationship form */}
      {showForm && (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50/50 p-3 space-y-2">
          <div className="flex gap-2">
            <select
              value={direction}
              onChange={(e) => setDirection(e.target.value as "outgoing" | "incoming")}
              className="rounded border px-2 py-1 text-xs"
            >
              <option value="outgoing">This rule &rarr;</option>
              <option value="incoming">&rarr; This rule</option>
            </select>
            <select
              value={relType}
              onChange={(e) => setRelType(e.target.value)}
              className="rounded border px-2 py-1 text-xs flex-1"
            >
              {RELATIONSHIP_TYPES.map((rt) => (
                <option key={rt.value} value={rt.value}>
                  {rt.label} — {rt.desc}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              placeholder="Target rule ID (UUID)"
              className="flex-1 rounded border px-2 py-1 text-xs font-mono"
            />
            <button
              onClick={handleCreate}
              disabled={submitting || !targetId.trim()}
              className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "..." : "Add"}
            </button>
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
        </div>
      )}

      {/* Relationship list */}
      {relationships.length === 0 ? (
        <p className="text-sm text-gray-500">No relationships.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {relationships.map((rel: Relationship, i: number) => {
            const isOutgoing = String(rel.source_id) === ruleId;
            const otherId = isOutgoing ? String(rel.target_id) : String(rel.source_id);
            return (
              <li key={i} className="flex items-center gap-2">
                {!isOutgoing && (
                  <span className="text-xs text-gray-400">&larr;</span>
                )}
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLORS[rel.relationship_type] || "bg-gray-100 text-gray-700"}`}>
                  {rel.relationship_type}
                </span>
                {isOutgoing && (
                  <span className="text-xs text-gray-400">&rarr;</span>
                )}
                <Link
                  href={`/rules/${otherId}`}
                  className="font-mono text-xs text-blue-600 hover:underline"
                >
                  {otherId.slice(0, 12)}...
                </Link>
                <span className="text-xs text-gray-300">
                  {new Date(rel.created_at).toLocaleDateString()}
                </span>
                <button
                  onClick={() => handleDelete(rel)}
                  className="ml-auto text-xs text-gray-300 hover:text-red-500"
                  title="Remove relationship"
                >
                  x
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
