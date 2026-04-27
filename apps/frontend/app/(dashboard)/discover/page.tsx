"use client";

import { useState, useCallback, useRef } from "react";
import {
  type DiscoveryCandidate,
  startDiscoveryScan,
  getScanStatus,
  getDiscoveryCandidates,
  approveCandidate,
  dismissCandidate,
} from "@/lib/api";

const SOURCE_OPTIONS = [
  { value: "claude_md", label: "CLAUDE.md" },
  { value: "linter_config", label: "Linter Config" },
  { value: "code_patterns", label: "Code Patterns" },
] as const;

type ScanPhase = "idle" | "scanning" | "completed" | "failed";

export default function DiscoverPage() {
  const [selectedSources, setSelectedSources] = useState<Set<string>>(
    new Set(SOURCE_OPTIONS.map((s) => s.value)),
  );
  const [fileContent, setFileContent] = useState("");
  const [repository, setRepository] = useState("");
  const [phase, setPhase] = useState<ScanPhase>("idle");
  const [candidates, setCandidates] = useState<DiscoveryCandidate[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const toggleSource = (value: string) => {
    setSelectedSources((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const handleScan = async () => {
    if (selectedSources.size === 0) {
      setError("Select at least one source type.");
      return;
    }

    setError("");
    setMessage("");
    setCandidates([]);
    setPhase("scanning");

    try {
      const fileContents: Record<string, string> = {};
      if (fileContent.trim()) {
        fileContents["claude_md"] = fileContent.trim();
      }

      const { scan_id } = await startDiscoveryScan(
        Array.from(selectedSources),
        fileContents,
        repository || undefined,
      );

      setMessage(`Scan started (${scan_id}). Polling for results...`);

      // Poll for completion
      pollingRef.current = setInterval(async () => {
        try {
          const status = await getScanStatus(scan_id);
          if (status.status === "completed") {
            stopPolling();
            const data = await getDiscoveryCandidates(scan_id);
            setCandidates(data.candidates);
            setPhase("completed");
            setMessage(
              `Scan complete. Found ${data.candidates.length} candidate rule(s).`,
            );
          } else if (status.status === "failed") {
            stopPolling();
            setPhase("failed");
            setError(status.error ?? "Scan failed.");
          }
        } catch {
          stopPolling();
          setPhase("failed");
          setError("Lost connection while polling scan status.");
        }
      }, 2000);
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "Failed to start scan.");
    }
  };

  const handleApprove = async (candidateId: string) => {
    try {
      await approveCandidate(candidateId);
      setCandidates((prev) =>
        prev.map((c) =>
          c.id === candidateId ? { ...c, status: "approved" } : c,
        ),
      );
      setMessage(`Candidate ${candidateId.slice(0, 8)} approved.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed.");
    }
  };

  const handleDismiss = async (candidateId: string) => {
    try {
      await dismissCandidate(candidateId);
      setCandidates((prev) =>
        prev.map((c) =>
          c.id === candidateId ? { ...c, status: "dismissed" } : c,
        ),
      );
      setMessage(`Candidate ${candidateId.slice(0, 8)} dismissed.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dismiss failed.");
    }
  };

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Rule Discovery</h1>
      <p className="mb-6 text-sm text-gray-500">
        Discover implicit rules from your codebase
      </p>

      {/* Scan configuration */}
      <div className="mb-8 rounded-lg border bg-white p-6">
        <h2 className="mb-3 text-lg font-medium">Configure Scan</h2>

        {/* Source checkboxes */}
        <fieldset className="mb-4">
          <legend className="mb-1 text-sm font-medium text-gray-700">
            Sources
          </legend>
          <div className="flex gap-4">
            {SOURCE_OPTIONS.map((opt) => (
              <label key={opt.value} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selectedSources.has(opt.value)}
                  onChange={() => toggleSource(opt.value)}
                />
                {opt.label}
              </label>
            ))}
          </div>
        </fieldset>

        {/* Repository name */}
        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Repository (optional)
          </label>
          <input
            type="text"
            value={repository}
            onChange={(e) => setRepository(e.target.value)}
            placeholder="e.g. my-org/my-repo"
            className="w-full max-w-md rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* File content textarea */}
        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Paste your CLAUDE.md content
          </label>
          <textarea
            value={fileContent}
            onChange={(e) => setFileContent(e.target.value)}
            rows={8}
            placeholder="Paste the contents of your CLAUDE.md or other configuration file here..."
            className="w-full rounded-md border px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <button
          onClick={handleScan}
          disabled={phase === "scanning"}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {phase === "scanning" ? "Scanning..." : "Scan"}
        </button>
      </div>

      {/* Messages */}
      {message && (
        <p className="mb-4 rounded bg-blue-50 px-4 py-2 text-sm text-blue-800">
          {message}
        </p>
      )}
      {error && (
        <p className="mb-4 rounded bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      {/* Candidates table */}
      {candidates.length > 0 && (
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-medium">
            Candidate Rules ({candidates.length})
          </h2>

          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-xs font-semibold uppercase tracking-wider text-gray-500">
                <th className="pb-2 pr-4">Statement</th>
                <th className="pb-2 pr-4">Source</th>
                <th className="pb-2 pr-4">Confidence</th>
                <th className="pb-2 pr-4">Status</th>
                <th className="pb-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {candidates.map((c) => (
                <CandidateRow
                  key={c.id}
                  candidate={c}
                  expanded={expandedId === c.id}
                  onToggle={() =>
                    setExpandedId(expandedId === c.id ? null : c.id)
                  }
                  onApprove={() => handleApprove(c.id)}
                  onDismiss={() => handleDismiss(c.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Candidate row sub-component
// ---------------------------------------------------------------------------

function CandidateRow({
  candidate,
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
  const c = candidate;
  const acted = c.status === "approved" || c.status === "dismissed";

  return (
    <>
      <tr
        className="cursor-pointer hover:bg-gray-50"
        onClick={onToggle}
      >
        <td className="py-3 pr-4">
          <span className="line-clamp-2">{c.statement}</span>
        </td>
        <td className="py-3 pr-4">
          <span className="rounded bg-purple-100 px-1.5 py-0.5 text-xs text-purple-800">
            {c.source_type}
          </span>
        </td>
        <td className="py-3 pr-4">{(c.confidence * 100).toFixed(0)}%</td>
        <td className="py-3 pr-4">
          <StatusBadge status={c.status} />
        </td>
        <td className="py-3">
          {!acted && (
            <div className="flex gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onApprove();
                }}
                className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700"
              >
                Approve
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDismiss();
                }}
                className="rounded bg-gray-200 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-300"
              >
                Dismiss
              </button>
            </div>
          )}
        </td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={5} className="bg-gray-50 px-4 py-3 text-sm">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2">
              <div>
                <dt className="text-xs font-semibold text-gray-500">Modality</dt>
                <dd>
                  <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-800">
                    {c.modality}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-gray-500">Severity</dt>
                <dd>
                  <span className="rounded bg-orange-100 px-1.5 py-0.5 text-xs text-orange-800">
                    {c.severity}
                  </span>
                </dd>
              </div>
              {c.scope.length > 0 && (
                <div>
                  <dt className="text-xs font-semibold text-gray-500">Scope</dt>
                  <dd className="flex flex-wrap gap-1">
                    {c.scope.map((s) => (
                      <span
                        key={s}
                        className="rounded bg-gray-200 px-1.5 py-0.5 text-xs"
                      >
                        {s}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
              {c.tags.length > 0 && (
                <div>
                  <dt className="text-xs font-semibold text-gray-500">Tags</dt>
                  <dd className="flex flex-wrap gap-1">
                    {c.tags.map((t) => (
                      <span
                        key={t}
                        className="rounded bg-gray-200 px-1.5 py-0.5 text-xs"
                      >
                        {t}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
              {c.rationale && (
                <div className="col-span-2">
                  <dt className="text-xs font-semibold text-gray-500">
                    Rationale
                  </dt>
                  <dd className="text-gray-700">{c.rationale}</dd>
                </div>
              )}
              {c.source_evidence && (
                <div className="col-span-2">
                  <dt className="text-xs font-semibold text-gray-500">
                    Source Evidence
                  </dt>
                  <dd className="whitespace-pre-wrap font-mono text-xs text-gray-600">
                    {c.source_evidence}
                  </dd>
                </div>
              )}
            </dl>
          </td>
        </tr>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    approved: "bg-green-100 text-green-800",
    dismissed: "bg-gray-100 text-gray-600",
  };
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-xs ${styles[status] ?? "bg-gray-100 text-gray-600"}`}
    >
      {status}
    </span>
  );
}
