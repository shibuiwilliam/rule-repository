"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import {
  type Federation,
  type EffectiveRule,
  type Rule,
  type RuleList,
  getFederations,
  createFederation,
  getFederation,
  getEffectiveRules,
  addRuleToFederation,
  removeRuleFromFederation,
} from "@/lib/api";

/* ---------- Style maps ---------- */

const LEVEL_COLORS: Record<string, string> = {
  organization: "bg-blue-100 text-blue-800",
  team: "bg-green-100 text-green-800",
  project: "bg-purple-100 text-purple-800",
};

const MODALITY_COLORS: Record<string, string> = {
  MUST: "bg-red-100 text-red-800",
  MUST_NOT: "bg-red-200 text-red-900",
  SHOULD: "bg-yellow-100 text-yellow-800",
  MAY: "bg-green-100 text-green-800",
  INFO: "bg-blue-100 text-blue-800",
};

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH: "bg-orange-500 text-white",
  MEDIUM: "bg-yellow-500 text-white",
  LOW: "bg-gray-400 text-white",
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/* ---------- Tree helpers ---------- */

function buildTree(federations: Federation[]): Federation[] {
  const map = new Map<string, Federation>();
  const roots: Federation[] = [];
  for (const f of federations) map.set(f.id, { ...f, children: [] });
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

/* ---------- Tree node ---------- */

function TreeNode({
  node,
  depth,
  selectedId,
  onSelect,
  directRuleCounts,
}: {
  node: Federation;
  depth: number;
  selectedId: string | null;
  onSelect: (f: Federation) => void;
  directRuleCounts: Map<string, number>;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedId === node.id;
  const ruleCount = directRuleCounts.get(node.id);

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
        {hasChildren ? (
          <span
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            className="mr-1 cursor-pointer text-gray-400 hover:text-gray-600"
          >
            {expanded ? "\u25BE" : "\u25B8"}
          </span>
        ) : (
          <span className="mr-1 w-3" />
        )}
        <span className="truncate flex-1">{node.name}</span>
        {ruleCount !== undefined && ruleCount > 0 && (
          <span className="rounded-full bg-gray-200 px-1.5 py-0.5 text-[10px] font-medium text-gray-600">
            {ruleCount}
          </span>
        )}
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${LEVEL_COLORS[node.level] ?? "bg-gray-100 text-gray-700"}`}>
          {node.level}
        </span>
      </button>
      {hasChildren && expanded && (
        <div>
          {node.children!.map((child: Federation) => (
            <TreeNode key={child.id} node={child} depth={depth + 1} selectedId={selectedId} onSelect={onSelect} directRuleCounts={directRuleCounts} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- Rule search picker ---------- */

function RuleSearchPicker({
  onAdd,
  existingRuleIds,
}: {
  onAdd: (ruleId: string, overrideRuleId?: string) => void;
  existingRuleIds: Set<string>;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Rule[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const doSearch = useCallback(async (q: string) => {
    setSearching(true);
    try {
      if (!q.trim()) {
        const res = await fetch(`${API_BASE}/api/v1/rules?page=1&page_size=15`);
        if (res.ok) { const data: RuleList = await res.json(); setResults(data.items); }
      } else {
        const res = await fetch(`${API_BASE}/api/v1/search/fulltext`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: q, page: 1, page_size: 15 }),
        });
        if (res.ok) {
          const data = await res.json();
          setResults((data.items ?? []).map((item: { rule: Rule }) => item.rule ?? item));
        }
      }
    } catch { /* ignore */ } finally { setSearching(false); }
  }, []);

  useEffect(() => {
    if (!showDropdown) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(query), 300);
    return () => clearTimeout(debounceRef.current);
  }, [query, showDropdown, doSearch]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setShowDropdown(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={dropdownRef} className="relative">
      <input
        type="text"
        className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        placeholder="Search rules to add..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => { setShowDropdown(true); if (results.length === 0) doSearch(query); }}
      />
      {showDropdown && (
        <div className="absolute z-10 mt-1 max-h-64 w-full overflow-auto rounded-md border bg-white shadow-lg">
          {searching && <div className="px-3 py-2 text-xs text-gray-400">Searching...</div>}
          {!searching && results.length === 0 && <div className="px-3 py-2 text-xs text-gray-400">{query ? "No rules found" : "No rules available"}</div>}
          {results.map((rule) => {
            const alreadyAdded = existingRuleIds.has(rule.id);
            return (
              <button
                key={rule.id}
                disabled={alreadyAdded}
                onClick={() => { onAdd(rule.id); setQuery(""); setShowDropdown(false); }}
                className={`flex w-full items-start gap-2 border-b px-3 py-2 text-left last:border-b-0 ${alreadyAdded ? "cursor-not-allowed bg-gray-50 opacity-50" : "hover:bg-indigo-50"}`}
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm">{rule.statement.length > 100 ? `${rule.statement.slice(0, 100)}...` : rule.statement}</p>
                  <div className="mt-1 flex gap-1.5">
                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${MODALITY_COLORS[rule.modality] ?? "bg-gray-100"}`}>{rule.modality}</span>
                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${SEVERITY_COLORS[rule.severity] ?? "bg-gray-300"}`}>{rule.severity}</span>
                  </div>
                </div>
                {alreadyAdded && <span className="mt-1 text-xs text-green-600">Added</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ---------- Create dialog ---------- */

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
    if (!name.trim()) { setError("Name is required"); return; }
    setSaving(true);
    setError("");
    try {
      await createFederation({
        name: name.trim(),
        level,
        parent_id: parentId || null,
        description: description.trim() || undefined,
        default_scope: defaultScope.split(",").map((s) => s.trim()).filter(Boolean),
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
        {error && <div className="mb-4 rounded-md bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>}
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" placeholder="e.g. Engineering Org" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Level</label>
            <select value={level} onChange={(e) => setLevel(e.target.value)} className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option value="organization">Organization</option>
              <option value="team">Team</option>
              <option value="project">Project</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Parent Federation</label>
            <select value={parentId ?? ""} onChange={(e) => setParentId(e.target.value || null)} className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option value="">None (root)</option>
              {federations.map((f) => (<option key={f.id} value={f.id}>{f.name} ({f.level})</option>))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" placeholder="Optional description..." />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Default Scope (comma-separated)</label>
            <input value={defaultScope} onChange={(e) => setDefaultScope(e.target.value)} className="w-full rounded-md border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" placeholder="e.g. backend, api, security" />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onClose} className="rounded-md border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">{saving ? "Creating..." : "Create"}</button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Main page ---------- */

interface DirectRule {
  rule_id: string;
  statement: string;
  modality: string;
  severity: string;
  override_parent_rule_id: string | null;
}

export default function FederationsPage() {
  const [federations, setFederations] = useState<Federation[]>([]);
  const [tree, setTree] = useState<Federation[]>([]);
  const [selected, setSelected] = useState<Federation | null>(null);
  const [directRules, setDirectRules] = useState<DirectRule[]>([]);
  const [effectiveRules, setEffectiveRules] = useState<EffectiveRule[]>([]);
  const [loadingRules, setLoadingRules] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [directRuleCounts, setDirectRuleCounts] = useState<Map<string, number>>(new Map());
  const [detailTab, setDetailTab] = useState<"effective" | "direct">("effective");

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

  useEffect(() => { loadFederations(); }, [loadFederations]);

  const handleSelect = useCallback(async (f: Federation) => {
    setSelected(f);
    setLoadingRules(true);
    setMessage("");
    try {
      const [effectiveData, detailData] = await Promise.all([
        getEffectiveRules(f.id),
        getFederation(f.id),
      ]);
      setEffectiveRules(effectiveData);
      setDirectRules(detailData.rules ?? []);
      // Update counts
      setDirectRuleCounts((prev) => {
        const next = new Map(prev);
        next.set(f.id, (detailData.rules ?? []).length);
        return next;
      });
    } catch {
      setEffectiveRules([]);
      setDirectRules([]);
    } finally {
      setLoadingRules(false);
    }
  }, []);

  const handleAddRule = async (ruleId: string, overrideParentRuleId?: string) => {
    if (!selected) return;
    try {
      await addRuleToFederation(selected.id, ruleId, overrideParentRuleId);
      setMessage("Rule added to federation.");
      await handleSelect(selected);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add rule");
    }
  };

  const handleRemoveRule = async (ruleId: string) => {
    if (!selected) return;
    try {
      await removeRuleFromFederation(selected.id, ruleId);
      setMessage("Rule removed from federation.");
      await handleSelect(selected);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove rule");
    }
  };

  const directRuleIds = new Set(directRules.map((r) => r.rule_id));

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900" title="Organize rules into org/team/project hierarchy with inheritance and overrides">Rule Federation</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage cross-project rule inheritance — organization, team, and project levels
        </p>
      </div>

      {error && <div className="mb-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {message && <div className="mb-4 rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">{message}</div>}

      <div className="flex gap-6">
        {/* Left column: federation tree */}
        <div className="w-1/3">
          <div className="rounded-lg border bg-white shadow-sm">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <h2 className="text-sm font-semibold text-gray-900">Federations</h2>
              <button onClick={() => setShowCreate(true)} className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700" title="Create a new federation node in the hierarchy">
                New
              </button>
            </div>
            <div className="p-2">
              {loading ? (
                <p className="px-3 py-4 text-center text-sm text-gray-500">Loading...</p>
              ) : tree.length === 0 ? (
                <p className="px-3 py-4 text-center text-sm text-gray-500">No federations yet. Create one to get started.</p>
              ) : (
                tree.map((node) => (
                  <TreeNode key={node.id} node={node} depth={0} selectedId={selected?.id ?? null} onSelect={handleSelect} directRuleCounts={directRuleCounts} />
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right column: detail panel */}
        <div className="w-2/3">
          {selected ? (
            <div className="space-y-4">
              {/* Header */}
              <div className="rounded-lg border bg-white p-5 shadow-sm">
                <div className="flex items-center gap-3">
                  <h2 className="text-lg font-semibold text-gray-900">{selected.name}</h2>
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${LEVEL_COLORS[selected.level] ?? "bg-gray-100 text-gray-700"}`}>
                    {selected.level}
                  </span>
                </div>
                {selected.description && <p className="mt-1 text-sm text-gray-500">{selected.description}</p>}
                {selected.default_scope && selected.default_scope.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {selected.default_scope.map((s: string) => (
                      <span key={s} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{s}</span>
                    ))}
                  </div>
                )}
                <p className="mt-2 font-mono text-xs text-gray-400">{selected.id}</p>
              </div>

              {/* Add rule */}
              <div className="rounded-lg border bg-white p-4 shadow-sm">
                <h3 className="mb-2 text-sm font-semibold text-gray-700">Add Rule to This Federation</h3>
                <RuleSearchPicker onAdd={handleAddRule} existingRuleIds={directRuleIds} />
              </div>

              {/* Tab selector */}
              <div className="flex gap-2">
                <button
                  onClick={() => setDetailTab("effective")}
                  className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${detailTab === "effective" ? "bg-indigo-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}
                >
                  Effective Rules ({effectiveRules.length})
                </button>
                <button
                  onClick={() => setDetailTab("direct")}
                  className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${detailTab === "direct" ? "bg-indigo-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}
                >
                  Direct Rules ({directRules.length})
                </button>
              </div>

              {/* Rules table */}
              <div className="rounded-lg border bg-white shadow-sm">
                {loadingRules ? (
                  <p className="px-6 py-8 text-center text-sm text-gray-500">Loading rules...</p>
                ) : detailTab === "effective" ? (
                  /* Effective rules */
                  effectiveRules.length === 0 ? (
                    <p className="px-6 py-8 text-center text-sm text-gray-500">No effective rules. Add rules directly or inherit from a parent federation.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            <th className="px-4 py-3">Statement</th>
                            <th className="px-4 py-3">Modality</th>
                            <th className="px-4 py-3">Severity</th>
                            <th className="px-4 py-3">Source</th>
                            <th className="px-4 py-3">Override</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {effectiveRules.map((rule) => {
                            const isInherited = rule.source_federation_id !== selected.id;
                            return (
                              <tr key={rule.rule_id} className="hover:bg-gray-50">
                                <td className="px-4 py-3">
                                  <Link href={`/rules/${rule.rule_id}`} className="text-sm text-blue-600 hover:underline">
                                    {rule.statement.length > 80 ? `${rule.statement.slice(0, 80)}...` : rule.statement}
                                  </Link>
                                </td>
                                <td className="px-4 py-3">
                                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${MODALITY_COLORS[rule.modality] ?? "bg-gray-100"}`}>{rule.modality}</span>
                                </td>
                                <td className="px-4 py-3">
                                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_COLORS[rule.severity] ?? "bg-gray-300"}`}>{rule.severity}</span>
                                </td>
                                <td className="px-4 py-3">
                                  <span className={`text-xs ${isInherited ? "text-gray-400 italic" : "text-gray-700 font-medium"}`}>
                                    {isInherited ? `inherited: ${rule.source_federation_name}` : "direct"}
                                  </span>
                                </td>
                                <td className="px-4 py-3">
                                  {rule.overrides && (
                                    <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
                                      overrides {rule.overrides.slice(0, 8)}...
                                    </span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )
                ) : (
                  /* Direct rules */
                  directRules.length === 0 ? (
                    <p className="px-6 py-8 text-center text-sm text-gray-500">No rules directly assigned. Use the search above to add rules.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            <th className="px-4 py-3">Statement</th>
                            <th className="px-4 py-3">Modality</th>
                            <th className="px-4 py-3">Severity</th>
                            <th className="px-4 py-3">Override</th>
                            <th className="px-4 py-3 text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {directRules.map((rule) => (
                            <tr key={rule.rule_id} className="hover:bg-gray-50">
                              <td className="px-4 py-3">
                                <Link href={`/rules/${rule.rule_id}`} className="text-sm text-blue-600 hover:underline">
                                  {rule.statement.length > 80 ? `${rule.statement.slice(0, 80)}...` : rule.statement}
                                </Link>
                              </td>
                              <td className="px-4 py-3">
                                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${MODALITY_COLORS[rule.modality] ?? "bg-gray-100"}`}>{rule.modality}</span>
                              </td>
                              <td className="px-4 py-3">
                                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_COLORS[rule.severity] ?? "bg-gray-300"}`}>{rule.severity}</span>
                              </td>
                              <td className="px-4 py-3">
                                {rule.override_parent_rule_id && (
                                  <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
                                    overrides {rule.override_parent_rule_id.slice(0, 8)}...
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <button
                                  onClick={() => handleRemoveRule(rule.rule_id)}
                                  className="rounded border px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                                >
                                  Remove
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )
                )}
              </div>
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center rounded-lg border bg-white shadow-sm">
              <p className="text-sm text-gray-500">Select a federation from the tree to manage its rules.</p>
            </div>
          )}
        </div>
      </div>

      {showCreate && (
        <CreateFederationDialog
          federations={federations}
          onCreated={() => { setShowCreate(false); loadFederations(); }}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  );
}
