"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Badge from "@/components/Badge";
import { useProject } from "@/lib/project-context";
import { searchDocumentsFulltext, searchDocumentsVector, searchDocumentsHybrid } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/* ---------- Types ---------- */

type SearchTab = "rules" | "documents";
type RuleSearchMode = "hybrid" | "fulltext" | "vector";
type DocSearchMode = "hybrid" | "fulltext" | "vector";

interface RuleResult {
  rule: {
    id: string;
    statement: string;
    modality: string;
    severity: string;
    status: string;
    scope: string[];
    tags: string[];
    rationale: string;
    context: string;
    preconditions: string[];
    exceptions: string[];
    following_examples: string[];
    violation_examples: string[];
    source_refs: Array<{
      document_id?: string;
      section?: string;
      page?: number;
    }>;
    created_at: string;
  };
  score: number;
}

interface DocResult {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
  uploaded_by: string;
  content_snippet: string;
  rules_extracted: number;
  relevance: number;
}

interface SourceDocInfo {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
}

const ALL_PROJECTS = "__all__";

/* ---------- Component ---------- */

export default function SearchPage() {
  const { currentProject, projects, loading: projectsLoading } = useProject();
  const [tab, setTab] = useState<SearchTab>("rules");
  const [query, setQuery] = useState("");
  const [ruleMode, setRuleMode] = useState<RuleSearchMode>("hybrid");
  const [docMode, setDocMode] = useState<DocSearchMode>("hybrid");

  // Project filter for search — independent of sidebar selector
  const [searchProjectId, setSearchProjectId] = useState<string>(ALL_PROJECTS);

  // Sync with sidebar project on initial load
  useEffect(() => {
    if (currentProject?.id) {
      setSearchProjectId(currentProject.id);
    }
  }, [currentProject?.id]);

  const [ruleResults, setRuleResults] = useState<RuleResult[]>([]);
  const [docResults, setDocResults] = useState<DocResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  // For "rules from document" drill-down
  const [sourceDoc, setSourceDoc] = useState<SourceDocInfo | null>(null);
  const [sourceRules, setSourceRules] = useState<RuleResult[]>([]);
  const [sourceTotal, setSourceTotal] = useState(0);

  /* ---- Build query param for project_id ---- */
  const projectParam =
    searchProjectId !== ALL_PROJECTS
      ? `?project_id=${searchProjectId}`
      : "";

  /* ---- Rule search ---- */
  const searchRules = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setSearched(false);
    setSourceDoc(null);
    setSourceRules([]);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/search/${ruleMode}${projectParam}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, page: 1, page_size: 30 }),
        },
      );
      if (!res.ok) throw new Error(`Search failed: ${res.status}`);
      const data = await res.json();
      setRuleResults(data.items ?? []);
      setTotal(data.total ?? 0);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  /* ---- Document search (title + content) ---- */
  const searchDocuments = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setSearched(false);
    setSourceDoc(null);
    setSourceRules([]);
    try {
      const pid = searchProjectId !== ALL_PROJECTS ? searchProjectId : undefined;
      const searchFn =
        docMode === "fulltext"
          ? searchDocumentsFulltext
          : docMode === "vector"
            ? searchDocumentsVector
            : searchDocumentsHybrid;
      const data = await searchFn(query, 1, 30, pid);
      setDocResults(data.items?.map((item) => ({
        id: item.document_id,
        filename: item.filename,
        mime_type: item.mime_type,
        size_bytes: item.size_bytes,
        uploaded_at: item.uploaded_at,
        uploaded_by: item.uploaded_by,
        content_snippet: item.snippet,
        rules_extracted: 0,
        relevance: item.score,
      })) ?? []);
      setTotal(data.total ?? 0);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  /* ---- Find rules from a specific document ---- */
  const findRulesFromDoc = async (docId: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/search/by-source-document${projectParam}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ document_id: docId, page: 1, page_size: 50 }),
        },
      );
      if (!res.ok) throw new Error(`Search failed: ${res.status}`);
      const data = await res.json();
      setSourceDoc(data.source_document ?? null);
      setSourceRules(data.items ?? []);
      setSourceTotal(data.total ?? 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (tab === "rules") searchRules();
    else searchDocuments();
  };

  const placeholder =
    tab === "rules"
      ? "Search rules by statement, scope, or keyword..."
      : "Search documents by filename or content...";

  const selectedProjectName =
    searchProjectId === ALL_PROJECTS
      ? "All Projects"
      : projects.find((p: { id: string; name: string }) => p.id === searchProjectId)?.name ?? "Unknown";

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Search</h1>

      {/* Tab bar */}
      <div className="mb-4 flex border-b">
        <button
          onClick={() => {
            setTab("rules");
            setSearched(false);
            setSourceDoc(null);
          }}
          className={`px-4 py-2 text-sm font-medium ${
            tab === "rules"
              ? "border-b-2 border-blue-600 text-blue-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
          title="Search natural-language rules by statement, rationale, or context"
        >
          Rules
        </button>
        <button
          onClick={() => {
            setTab("documents");
            setSearched(false);
            setSourceDoc(null);
          }}
          className={`px-4 py-2 text-sm font-medium ${
            tab === "documents"
              ? "border-b-2 border-blue-600 text-blue-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
          title="Search uploaded documents by filename or content"
        >
          Documents
        </button>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSubmit} className="mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="flex-1 rounded-md border px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {tab === "rules" && (
            <select
              value={ruleMode}
              onChange={(e) => setRuleMode(e.target.value as RuleSearchMode)}
              className="rounded-md border px-3 py-2 text-sm"
              title="Search algorithm: Hybrid combines text and semantic matching for best results"
            >
              <option value="hybrid">Hybrid</option>
              <option value="fulltext">Full-text</option>
              <option value="vector">Semantic</option>
            </select>
          )}
          {tab === "documents" && (
            <select
              value={docMode}
              onChange={(e) => setDocMode(e.target.value as DocSearchMode)}
              className="rounded-md border px-3 py-2 text-sm"
              title="Search algorithm: Hybrid combines text and semantic matching for best results"
            >
              <option value="hybrid">Hybrid</option>
              <option value="fulltext">Full-text</option>
              <option value="vector">Semantic</option>
            </select>
          )}

          {/* Project filter */}
          <select
            value={searchProjectId}
            onChange={(e) => setSearchProjectId(e.target.value)}
            disabled={projectsLoading}
            className="rounded-md border px-3 py-2 text-sm"
            title="Filter search results to a specific project, or search across all"
          >
            <option value={ALL_PROJECTS}>All Projects</option>
            {projects.map((p: { id: string; name: string }) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </form>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {/* ---- Source document drill-down panel ---- */}
      {sourceDoc && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <DocIcon />
              <div>
                <p className="text-sm font-medium text-blue-900">
                  Rules from: {sourceDoc.filename}
                </p>
                <p className="text-xs text-blue-600">
                  {sourceTotal} rule{sourceTotal !== 1 ? "s" : ""} extracted
                  from this document
                </p>
              </div>
            </div>
            <button
              onClick={() => {
                setSourceDoc(null);
                setSourceRules([]);
              }}
              className="text-xs text-blue-500 hover:underline"
            >
              Clear
            </button>
          </div>

          {sourceRules.length > 0 && (
            <div className="mt-3 space-y-2">
              {sourceRules.map((item) => (
                <RuleCard key={item.rule.id} item={item} onFindRulesFromDoc={findRulesFromDoc} />
              ))}
            </div>
          )}
          {sourceRules.length === 0 && (
            <p className="mt-3 text-sm text-blue-700">
              No rules have been extracted from this document yet.
            </p>
          )}
        </div>
      )}

      {/* Result count */}
      {searched && !sourceDoc && (
        <p className="mb-4 text-sm text-gray-600">
          {total} result{total !== 1 ? "s" : ""} for &ldquo;{query}&rdquo;
          {searchProjectId !== ALL_PROJECTS && (
            <span className="ml-1 text-gray-400">
              in {selectedProjectName}
            </span>
          )}
        </p>
      )}

      {/* ---- Rule results ---- */}
      {tab === "rules" && searched && !sourceDoc && (
        <div className="space-y-3">
          {ruleResults.map((item) => (
            <RuleCard key={item.rule.id} item={item} onFindRulesFromDoc={findRulesFromDoc} />
          ))}
          {ruleResults.length === 0 && (
            <p className="text-sm text-gray-500">No rules found.</p>
          )}
        </div>
      )}

      {/* ---- Document results ---- */}
      {tab === "documents" && searched && !sourceDoc && (
        <div className="space-y-3">
          {docResults.map((doc) => (
            <div
              key={doc.id}
              className="rounded-lg border bg-white p-4 shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <DocIcon />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{doc.filename}</p>
                    <p className="mt-0.5 text-xs text-gray-500">
                      {doc.mime_type} &middot;{" "}
                      {(doc.size_bytes / 1024).toFixed(1)} KB &middot;{" "}
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </p>
                    {doc.content_snippet && (
                      <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-gray-600">
                        {doc.content_snippet}
                      </p>
                    )}
                  </div>
                </div>
                <div className="ml-4 flex flex-col items-end gap-1">
                  {doc.rules_extracted > 0 ? (
                    <button
                      onClick={() => findRulesFromDoc(doc.id)}
                      className="rounded-md bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-100"
                    >
                      {doc.rules_extracted} rule{doc.rules_extracted !== 1 ? "s" : ""} &rarr;
                    </button>
                  ) : (
                    <span className="rounded-md bg-gray-50 px-3 py-1.5 text-xs text-gray-400">
                      No rules
                    </span>
                  )}
                  {doc.relevance > 0 && (
                    <span className="text-xs text-gray-400">
                      relevance: {doc.relevance.toFixed(3)}
                    </span>
                  )}
                </div>
              </div>
              <p className="mt-1 font-mono text-xs text-gray-300">
                {doc.id}
              </p>
            </div>
          ))}
          {docResults.length === 0 && (
            <p className="text-sm text-gray-500">No documents found.</p>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------- Sub-components ---------- */

function DocIcon() {
  return (
    <svg
      className="h-5 w-5 flex-shrink-0 text-gray-400"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  );
}

function RuleCard({
  item,
  onFindRulesFromDoc,
}: {
  item: RuleResult;
  onFindRulesFromDoc: (docId: string) => void;
}) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <Link
          href={`/rules/${item.rule.id}`}
          className="text-sm font-medium text-blue-600 hover:underline"
        >
          {item.rule.statement.length > 200
            ? `${item.rule.statement.slice(0, 200)}...`
            : item.rule.statement}
        </Link>
        {item.score < 1.0 && (
          <span className="ml-2 whitespace-nowrap text-xs text-gray-400">
            {item.score.toFixed(3)}
          </span>
        )}
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        <Badge label={item.rule.modality} variant="modality" />
        <Badge label={item.rule.severity} variant="severity" />
        <Badge label={item.rule.status} variant="status" />
        {item.rule.tags.map((tag: string) => (
          <Badge key={tag} label={tag} variant="tag" />
        ))}
      </div>

      {/* Conditions preview */}
      {(item.rule.preconditions?.length > 0 || item.rule.exceptions?.length > 0) && (
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
          {item.rule.preconditions?.length > 0 && (
            <span>When: {item.rule.preconditions.slice(0, 2).join("; ")}{item.rule.preconditions.length > 2 ? ` (+${item.rule.preconditions.length - 2})` : ""}</span>
          )}
          {item.rule.exceptions?.length > 0 && (
            <span>Unless: {item.rule.exceptions.slice(0, 1).join("; ")}{item.rule.exceptions.length > 1 ? ` (+${item.rule.exceptions.length - 1})` : ""}</span>
          )}
        </div>
      )}

      {/* Source document link */}
      {item.rule.source_refs && item.rule.source_refs.length > 0 && (
        <div className="mt-2 flex items-center gap-1.5 text-xs text-gray-500">
          <DocIcon />
          <span>Source:</span>
          {item.rule.source_refs.map(
            (ref, i) =>
              ref.document_id && (
                <button
                  key={i}
                  onClick={() => onFindRulesFromDoc(ref.document_id!)}
                  className="font-mono text-blue-500 hover:underline"
                >
                  {ref.document_id.slice(0, 8)}...
                  {ref.page != null && ` p.${ref.page}`}
                </button>
              ),
          )}
        </div>
      )}
    </div>
  );
}
