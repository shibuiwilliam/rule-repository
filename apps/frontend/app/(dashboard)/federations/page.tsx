"use client";

import { useState, useEffect, useCallback } from "react";
import {
  type Federation,
  type EffectiveRule,
  getFederations,
  createFederation,
  getEffectiveRules,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Level badge colors
// ---------------------------------------------------------------------------

const LEVEL_COLORS: Record<string, string> = {
  organization: "bg-blue-100 text-blue-800",
  team: "bg-green-100 text-green-800",
  project: "bg-purple-100 text-purple-800",
};

const MODALITY_COLORS: Record<string, string> = {
  must: "bg-red-100 text-red-800",
  should: "bg-yellow-100 text-yellow-800",
  may: "bg-gray-100 text-gray-700",
  must_not: "bg-red-200 text-red-900",
  should_not: "bg-orange-100 text-orange-800",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-700",
};

// ---------------------------------------------------------------------------
// Tree helpers
// ---------------------------------------------------------------------------

function buildTree(federations: Federation[]): Federation[] {
  const map = new Map<string, Federation>();
  const roots: Federation[] = [];

  for (const f of federations) {
    map.set(f.id, { ...f, children: [] });
  }

  for (const f of federations) {
    const node = map.get(f.id)!;
    if (f.parent_id && map.has(f.parent_id)) {
      map.get(f.parent_id)!.children!.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

function countRulesInSubtree(_node: Federation): string {
  // We don't have rule counts in the list response, so just show level
  return "";
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function TreeNode({
  node,
  depth,
  selectedId,
  onSelect,
}: {
  node: Federation;
  depth: number;
  selectedId: string | null;
  onSelect: (f: Federation) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedId === node.id;

  return (
    <div>
      <button
        onClick={() => onSelect(node)}
        className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors ${
          isSelected
            ? "bg-indigo-50 text-indigo-900 font-medium"
            : "text-gray-700 hover:bg-gray-100"
        }`}
        style={{ paddingLeft: `${depth * 16 + 12}px` }}
      >
        {hasChildren && (
          <span
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="mr-1 cursor-pointer text-gray-400 hover:text-gray-600"
          >
            {expanded ? "\u25BE" : "\u25B8"}
          </span>
        )}
        {!hasChildren && <span className="mr-1 w-3" />}
        <span className="truncate flex-1">{node.name}</span>
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
            LEVEL_COLORS[node.level] ?? "bg-gray-100 text-gray-700"
          }`}
        >
          {node.level}
        </span>
      </button>
      {hasChildren && expanded && (
        <div>
          {node.children!.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create dialog
// ---------------------------------------------------------------------------

function CreateFederationDialog({
  federations,
  onCreated,
  onClose,
}: {
  federations: Federation[];
  onCreated: () => void;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const [level, setLevel] = useState("organization");
  const [parentId, setParentId] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [defaultScope, setDefaultScope] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await createFederation({
        name: name.trim(),
        level,
        parent_id: parentId || null,
        description: description.trim() || undefined,
        default_scope: defaultScope
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create federation");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Create Federation</h2>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>
        )}

        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="e.g. Engineering Org"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Level</label>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="organization">Organization</option>
              <option value="team">Team</option>
              <option value="project">Project</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Parent Federation
            </label>
            <select
              value={parentId ?? ""}
              onChange={(e) => setParentId(e.target.value || null)}
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">None (root)</option>
              {federations.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} ({f.level})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="Optional description..."
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Default Scope (comma-separated)
            </label>
            <input
              value={defaultScope}
              onChange={(e) => setDefaultScope(e.target.value)}
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="e.g. backend, api, security"
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-md border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? "Creating..." : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function FederationsPage() {
  const [federations, setFederations] = useState<Federation[]>([]);
  const [tree, setTree] = useState<Federation[]>([]);
  const [selected, setSelected] = useState<Federation | null>(null);
  const [effectiveRules, setEffectiveRules] = useState<EffectiveRule[]>([]);
  const [loadingRules, setLoadingRules] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadFederations = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getFederations();
      setFederations(data);
      setTree(buildTree(data));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load federations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFederations();
  }, [loadFederations]);

  const handleSelect = useCallback(async (f: Federation) => {
    setSelected(f);
    setLoadingRules(true);
    try {
      const rules = await getEffectiveRules(f.id);
      setEffectiveRules(rules);
    } catch {
      setEffectiveRules([]);
    } finally {
      setLoadingRules(false);
    }
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Rule Federation</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage cross-project rule inheritance
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <div className="flex gap-6">
        {/* Left column: federation tree */}
        <div className="w-1/3">
          <div className="rounded-lg border bg-white shadow-sm">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <h2 className="text-sm font-semibold text-gray-900">Federations</h2>
              <button
                onClick={() => setShowCreate(true)}
                className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
              >
                Create Federation
              </button>
            </div>

            <div className="p-2">
              {loading ? (
                <p className="px-3 py-4 text-center text-sm text-gray-500">Loading...</p>
              ) : tree.length === 0 ? (
                <p className="px-3 py-4 text-center text-sm text-gray-500">
                  No federations yet. Create one to get started.
                </p>
              ) : (
                tree.map((node) => (
                  <TreeNode
                    key={node.id}
                    node={node}
                    depth={0}
                    selectedId={selected?.id ?? null}
                    onSelect={handleSelect}
                  />
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right column: selected federation detail */}
        <div className="w-2/3">
          {selected ? (
            <div className="rounded-lg border bg-white shadow-sm">
              {/* Header */}
              <div className="border-b px-6 py-4">
                <div className="flex items-center gap-3">
                  <h2 className="text-lg font-semibold text-gray-900">{selected.name}</h2>
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      LEVEL_COLORS[selected.level] ?? "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {selected.level}
                  </span>
                </div>
                {selected.description && (
                  <p className="mt-1 text-sm text-gray-500">{selected.description}</p>
                )}
                {selected.default_scope.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {selected.default_scope.map((s) => (
                      <span
                        key={s}
                        className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Effective rules */}
              <div className="px-6 py-4">
                <h3 className="mb-3 text-sm font-semibold text-gray-900">Effective Rules</h3>

                {loadingRules ? (
                  <p className="py-4 text-center text-sm text-gray-500">Loading rules...</p>
                ) : effectiveRules.length === 0 ? (
                  <p className="py-4 text-center text-sm text-gray-500">
                    No effective rules for this federation.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          <th className="pb-2 pr-4">Statement</th>
                          <th className="pb-2 pr-4">Modality</th>
                          <th className="pb-2 pr-4">Severity</th>
                          <th className="pb-2 pr-4">Source</th>
                          <th className="pb-2">Override</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {effectiveRules.map((rule) => {
                          const isInherited = rule.source_federation_id !== selected.id;
                          return (
                            <tr key={rule.rule_id} className="hover:bg-gray-50">
                              <td className="py-2.5 pr-4">
                                <span className="line-clamp-2 text-gray-900">
                                  {rule.statement}
                                </span>
                              </td>
                              <td className="py-2.5 pr-4">
                                <span
                                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                                    MODALITY_COLORS[rule.modality] ?? "bg-gray-100 text-gray-700"
                                  }`}
                                >
                                  {rule.modality}
                                </span>
                              </td>
                              <td className="py-2.5 pr-4">
                                <span
                                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                                    SEVERITY_COLORS[rule.severity] ?? "bg-gray-100 text-gray-700"
                                  }`}
                                >
                                  {rule.severity}
                                </span>
                              </td>
                              <td className="py-2.5 pr-4">
                                <span
                                  className={`text-xs ${
                                    isInherited ? "text-gray-400" : "text-gray-700 font-medium"
                                  }`}
                                >
                                  {rule.source_federation_name}
                                </span>
                              </td>
                              <td className="py-2.5">
                                {rule.overrides && (
                                  <span className="inline-flex items-center rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
                                    Overrides {rule.overrides.slice(0, 8)}...
                                  </span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center rounded-lg border bg-white shadow-sm">
              <p className="text-sm text-gray-500">
                Select a federation from the tree to view its details and effective rules.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Create dialog */}
      {showCreate && (
        <CreateFederationDialog
          federations={federations}
          onCreated={() => {
            setShowCreate(false);
            loadFederations();
          }}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  );
}
