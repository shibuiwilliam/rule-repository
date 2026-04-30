"use client";

import { useState, useCallback, useRef } from "react";
import Badge from "@/components/Badge";
import {
  type DiscoveryCandidate,
  startDiscoveryScan,
  getDiscoveryCandidates,
  approveCandidate,
  dismissCandidate,
} from "@/lib/api";
import { useProject } from "@/lib/project-context";

/* ---------- Constants ---------- */

const SOURCE_OPTIONS = [
  {
    value: "policy_document",
    label: "Policy Documents",
    description: "HR policies, legal contracts, compliance handbooks, safety regulations",
  },
  {
    value: "claude_md",
    label: "CLAUDE.md / AGENTS.md",
    description: "Agent instruction files with deontic keywords",
  },
  {
    value: "linter_config",
    label: "Linter Config",
    description: "ruff.toml, .eslintrc, tsconfig.json, .prettierrc",
  },
  {
    value: "code_patterns",
    label: "Code Patterns",
    description: "Naming conventions, import patterns, docstring coverage",
  },
] as const;

type ScanPhase = "idle" | "scanning" | "completed" | "failed";

interface FileEntry {
  name: string;
  content: string;
}

/* ---------- Component ---------- */

export default function DiscoverPage() {
  const { currentProject } = useProject();
  const [selectedSources, setSelectedSources] = useState<Set<string>>(
    new Set(["policy_document", "claude_md"]),
  );
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [repository, setRepository] = useState("");
  const [phase, setPhase] = useState<ScanPhase>("idle");
  const [candidates, setCandidates] = useState<DiscoveryCandidate[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /* ---- Source selection ---- */
  const toggleSource = (value: string) => {
    setSelectedSources((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  /* ---- File management ---- */
  const addFiles = useCallback(async (fileList: FileList | File[]) => {
    const newEntries: FileEntry[] = [];
    for (const file of Array.from(fileList)) {
      try {
        const content = await file.text();
        newEntries.push({ name: file.name, content });
      } catch {
        // skip binary files that can't be read as text
      }
    }
    setFiles((prev) => [...prev, ...newEntries]);
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
      e.target.value = "";
    }
  };

  /* ---- Scan ---- */
  const handleScan = async () => {
    if (selectedSources.size === 0) {
      setError("Select at least one source type.");
      return;
    }
    if (files.length === 0) {
      setError("Add at least one file to scan.");
      return;
    }

    setError("");
    setMessage("");
    setCandidates([]);
    setPhase("scanning");

    try {
      // Build file_contents map: filename → content
      const fileContents: Record<string, string> = {};
      for (const f of files) {
        fileContents[f.name] = f.content;
      }

      setMessage(`Scanning ${files.length} file(s) — this may take a minute...`);

      // The backend runs the scan synchronously: when the POST returns,
      // the scan is already completed with all candidates in the database.
      const { scan_id } = await startDiscoveryScan(
        Array.from(selectedSources),
        fileContents,
        repository || undefined,
        currentProject?.id,
      );

      // Fetch the candidates directly — no polling needed since the scan
      // completed during the POST request.
      const data = await getDiscoveryCandidates(scan_id);
      setCandidates(data);
      setPhase("completed");
      setMessage(`Found ${data.length} candidate rule(s).`);
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "Failed to start scan.");
    }
  };

  /* ---- Candidate actions ---- */
  const handleApprove = async (id: string) => {
    try {
      await approveCandidate(id);
      setCandidates((prev) =>
        prev.map((c) => (c.id === id ? { ...c, status: "approved" } : c)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed.");
    }
  };

  const handleDismiss = async (id: string) => {
    try {
      await dismissCandidate(id);
      setCandidates((prev) =>
        prev.map((c) => (c.id === id ? { ...c, status: "dismissed" } : c)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dismiss failed.");
    }
  };

  const handleApproveAll = async () => {
    const pending = candidates.filter((c) => c.status === "pending");
    for (const c of pending) {
      await handleApprove(c.id);
    }
    setMessage(`Approved ${pending.length} candidate(s).`);
  };

  const handleDismissAll = async () => {
    const pending = candidates.filter((c) => c.status === "pending");
    for (const c of pending) {
      await handleDismiss(c.id);
    }
    setMessage(`Dismissed ${pending.length} candidate(s).`);
  };

  const pendingCount = candidates.filter((c) => c.status === "pending").length;

  /* ---- Render ---- */
  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Rule Discovery</h1>
      <p className="mb-6 text-sm text-gray-500">
        Discover rules from any document — policies, contracts, handbooks, code standards, or configuration files
      </p>

      {/* ============ Scan Configuration ============ */}
      <div className="mb-8 rounded-lg border bg-white p-6">
        {/* Source type selection */}
        <fieldset className="mb-5">
          <legend className="mb-2 text-sm font-medium text-gray-700">
            What to look for
          </legend>
          <div className="grid grid-cols-2 gap-3">
            {SOURCE_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                  selectedSources.has(opt.value)
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedSources.has(opt.value)}
                  onChange={() => toggleSource(opt.value)}
                  className="mt-0.5"
                />
                <div>
                  <p className="text-sm font-medium">{opt.label}</p>
                  <p className="text-xs text-gray-500">{opt.description}</p>
                </div>
              </label>
            ))}
          </div>
        </fieldset>

        {/* File drop zone */}
        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Files to scan
          </label>
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={(e) => { e.preventDefault(); setDragging(false); }}
            onClick={() => fileInputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
              dragging
                ? "border-blue-500 bg-blue-50"
                : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
            }`}
          >
            <svg className="mb-1.5 h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-sm text-gray-600">
              {dragging ? "Drop files here..." : "Drop files here, or click to browse"}
            </p>
            <p className="mt-1 text-xs text-gray-400">
              Any text file: .md, .txt, .rst, .policy, CLAUDE.md, ruff.toml, .eslintrc, .py, etc.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileInput}
              className="hidden"
            />
          </div>
        </div>

        {/* File list */}
        {files.length > 0 && (
          <div className="mb-4">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs font-medium text-gray-500">
                {files.length} file(s) loaded
              </span>
              <button
                onClick={() => setFiles([])}
                className="text-xs text-red-500 hover:underline"
              >
                Remove all
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {files.map((f, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1.5 rounded-full border bg-gray-50 px-3 py-1 text-xs"
                >
                  <svg className="h-3 w-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {f.name}
                  <span className="text-gray-400">
                    ({(f.content.length / 1024).toFixed(1)}K)
                  </span>
                  <button
                    onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                    className="ml-0.5 text-gray-400 hover:text-red-500"
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Repository (optional) */}
        <div className="mb-5">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Repository or project name <span className="text-gray-400">(optional)</span>
          </label>
          <input
            type="text"
            value={repository}
            onChange={(e) => setRepository(e.target.value)}
            placeholder="e.g. acme-corp/employee-handbook"
            className="w-full max-w-md rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Scan button */}
        <button
          onClick={handleScan}
          disabled={phase === "scanning" || files.length === 0}
          className="rounded-md bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {phase === "scanning" ? "Scanning..." : `Scan ${files.length} file(s)`}
        </button>
      </div>

      {/* ============ Messages ============ */}
      {message && (
        <p className="mb-4 rounded bg-blue-50 px-4 py-2 text-sm text-blue-800">{message}</p>
      )}
      {error && (
        <p className="mb-4 rounded bg-red-50 px-4 py-2 text-sm text-red-800">{error}</p>
      )}

      {/* ============ Candidates ============ */}
      {candidates.length > 0 && (
        <div className="rounded-lg border bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-medium">
              Candidate Rules ({candidates.length})
            </h2>
            {pendingCount > 0 && (
              <div className="flex gap-2">
                <button
                  onClick={handleApproveAll}
                  className="rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
                >
                  Approve All ({pendingCount})
                </button>
                <button
                  onClick={handleDismissAll}
                  className="rounded border px-3 py-1.5 text-xs font-medium hover:bg-gray-50"
                >
                  Dismiss All
                </button>
              </div>
            )}
          </div>

          <div className="space-y-2">
            {candidates.map((c) => (
              <CandidateCard
                key={c.id}
                candidate={c}
                expanded={expandedId === c.id}
                onToggle={() => setExpandedId(expandedId === c.id ? null : c.id)}
                onApprove={() => handleApprove(c.id)}
                onDismiss={() => handleDismiss(c.id)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- Candidate Card ---------- */

function CandidateCard({
  candidate: c,
  expanded,
  onToggle,
  onApprove,
  onDismiss,
}: {
  candidate: DiscoveryCandidate;
  expanded: boolean;
  onToggle: () => void;
  onApprove: () => void;
  onDismiss: () => void;
}) {
  const acted = c.status !== "pending";

  return (
    <div className={`rounded-lg border ${acted ? "opacity-60" : ""}`}>
      <div
        className="flex cursor-pointer items-start gap-3 p-3 hover:bg-gray-50"
        onClick={onToggle}
      >
        {/* Expand chevron */}
        <svg
          className={`mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>

        {/* Statement + badges */}
        <div className="min-w-0 flex-1">
          <p className="text-sm">{c.statement}</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            <Badge label={c.modality} variant="modality" />
            <Badge label={c.severity} variant="severity" />
            <span className="rounded bg-purple-100 px-1.5 py-0.5 text-xs text-purple-800">
              {c.source_type.replace("_", " ")}
            </span>
            <span className="text-xs text-gray-400">
              {(c.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Status + actions */}
        <div className="flex items-center gap-2">
          <StatusBadge status={c.status} />
          {!acted && (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); onApprove(); }}
                className="rounded bg-green-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-700"
              >
                Approve
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onDismiss(); }}
                className="rounded bg-gray-200 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-300"
              >
                Dismiss
              </button>
            </>
          )}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t bg-gray-50 px-4 py-3">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            {c.scope.length > 0 && (
              <div>
                <dt className="text-xs font-semibold text-gray-500">Scope</dt>
                <dd className="flex flex-wrap gap-1">
                  {c.scope.map((s: string) => (
                    <span key={s} className="rounded bg-gray-200 px-1.5 py-0.5 text-xs">{s}</span>
                  ))}
                </dd>
              </div>
            )}
            {c.tags.length > 0 && (
              <div>
                <dt className="text-xs font-semibold text-gray-500">Tags</dt>
                <dd className="flex flex-wrap gap-1">
                  {c.tags.map((t: string) => (
                    <span key={t} className="rounded bg-gray-200 px-1.5 py-0.5 text-xs">{t}</span>
                  ))}
                </dd>
              </div>
            )}
            {c.rationale && (
              <div className="col-span-2">
                <dt className="text-xs font-semibold text-gray-500">Rationale</dt>
                <dd className="text-gray-700">{c.rationale}</dd>
              </div>
            )}
            {c.source_evidence && (
              <div className="col-span-2">
                <dt className="text-xs font-semibold text-gray-500">Source Evidence</dt>
                <dd className="whitespace-pre-wrap font-mono text-xs text-gray-600">
                  {c.source_evidence}
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

/* ---------- Status Badge ---------- */

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    approved: "bg-green-100 text-green-800",
    dismissed: "bg-gray-100 text-gray-600",
  };
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs ${styles[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}
