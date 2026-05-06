"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Badge from "@/components/Badge";
import { useProject } from "@/lib/project-context";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DocSummary {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
  uploaded_by: string;
}

interface DocDetail extends DocSummary {
  content_text: string | null;
  extractions: {
    id: string;
    status: string;
    model_id: string;
    candidates_count: number;
    extracted_at: string;
  }[];
}

interface LinkedRule {
  rule: {
    id: string;
    statement: string;
    modality: string;
    severity: string;
    status: string;
    scope: string[];
    tags: string[];
    created_at: string;
  };
  score: number;
}

interface Candidate {
  index: number;
  statement: string;
  modality: string;
  severity: string;
  confidence: number;
}

type BulkDocStatus = "pending" | "extracting" | "done" | "error";

interface BulkDocResult {
  docId: string;
  filename: string;
  status: BulkDocStatus;
  extractionId?: string;
  candidates: Candidate[];
  error?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DocumentsPage() {
  const { currentProject } = useProject();
  // --- Registered documents list ---
  const [registeredDocs, setRegisteredDocs] = useState<DocSummary[]>([]);
  const [totalDocs, setTotalDocs] = useState(0);
  const [loadingDocs, setLoadingDocs] = useState(true);

  // --- Detail view (single doc mode) ---
  const [selectedDoc, setSelectedDoc] = useState<DocDetail | null>(null);
  const [linkedRules, setLinkedRules] = useState<LinkedRule[]>([]);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // --- Upload ---
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [dragging, setDragging] = useState(false);
  const [message, setMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Single-doc extraction ---
  const [extracting, setExtracting] = useState(false);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [extractionId, setExtractionId] = useState("");
  const [selectedCandidates, setSelectedCandidates] = useState<Set<number>>(new Set());

  // --- Bulk extraction ---
  const [bulkSelected, setBulkSelected] = useState<Set<string>>(new Set());
  const [bulkMode, setBulkMode] = useState(false);
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkResults, setBulkResults] = useState<BulkDocResult[]>([]);
  const [bulkApprovals, setBulkApprovals] = useState<Map<string, Set<number>>>(new Map());

  // --- Toggles ---
  const [showRules, setShowRules] = useState(true);

  // ---------------------------------------------------------------------------
  // Load registered documents on mount
  // ---------------------------------------------------------------------------

  const loadDocuments = useCallback(async () => {
    setLoadingDocs(true);
    try {
      const projectParam = currentProject?.id ? `&project_id=${currentProject.id}` : "";
      const res = await fetch(`${API_BASE}/api/v1/documents?page=1&page_size=100${projectParam}`);
      if (res.ok) {
        const data = await res.json();
        setRegisteredDocs(data.items ?? []);
        setTotalDocs(data.total ?? 0);
      }
    } catch {
      // silent
    } finally {
      setLoadingDocs(false);
    }
  }, [currentProject?.id]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // ---------------------------------------------------------------------------
  // Select a document → load detail + linked rules (single-doc mode)
  // ---------------------------------------------------------------------------

  const selectDocument = async (docId: string) => {
    if (bulkMode) return; // don't open detail in bulk mode
    setLoadingDetail(true);
    setSelectedDoc(null);
    setLinkedRules([]);
    setCandidates([]);
    setExtractionId("");
    setSelectedCandidates(new Set());
    setBulkResults([]);

    try {
      const detailRes = await fetch(`${API_BASE}/api/v1/documents/${docId}`);
      if (!detailRes.ok) throw new Error("Failed to load document");
      const detail: DocDetail = await detailRes.json();
      setSelectedDoc(detail);

      const rulesRes = await fetch(`${API_BASE}/api/v1/search/by-source-document`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: docId, page: 1, page_size: 100 }),
      });
      if (rulesRes.ok) {
        const rulesData = await rulesRes.json();
        setLinkedRules(rulesData.items ?? []);
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to load document");
    } finally {
      setLoadingDetail(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Upload
  // ---------------------------------------------------------------------------

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      const fileArray = Array.from(files);
      if (fileArray.length === 0) return;

      setUploading(true);
      setMessage("");
      let uploaded = 0;

      for (let i = 0; i < fileArray.length; i++) {
        setUploadProgress(`Uploading ${i + 1} of ${fileArray.length}: ${fileArray[i].name}`);
        const formData = new FormData();
        formData.append("file", fileArray[i]);
        try {
          const uploadParam = currentProject?.id ? `?project_id=${currentProject.id}` : "";
          const res = await fetch(`${API_BASE}/api/v1/documents/upload${uploadParam}`, {
            method: "POST",
            body: formData,
          });
          if (res.ok) uploaded++;
        } catch {
          // continue with next file
        }
      }

      setUploadProgress("");
      setUploading(false);
      setMessage(`Uploaded ${uploaded} of ${fileArray.length} file(s).`);
      loadDocuments();
    },
    [loadDocuments],
  );

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length > 0) uploadFiles(e.dataTransfer.files);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(e.target.files);
      e.target.value = "";
    }
  };

  // ---------------------------------------------------------------------------
  // Single-doc extraction
  // ---------------------------------------------------------------------------

  const handleExtract = async () => {
    if (!selectedDoc) return;
    setExtracting(true);
    setCandidates([]);
    try {
      const res = await fetch(`${API_BASE}/api/v1/documents/${selectedDoc.id}/extract`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`Extraction failed: ${res.status}`);
      const data = await res.json();
      setCandidates(data.candidates ?? []);
      setExtractionId(data.extraction_id);
      setMessage(`Extracted ${data.candidates?.length ?? 0} candidates from ${selectedDoc.filename}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Extraction failed");
    } finally {
      setExtracting(false);
    }
  };

  const handleApprove = async () => {
    if (!extractionId || selectedCandidates.size === 0) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/documents/extractions/${extractionId}/review`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            extraction_id: extractionId,
            approved_indices: Array.from(selectedCandidates),
          }),
        },
      );
      if (!res.ok) throw new Error("Review failed");
      const data = await res.json();
      setMessage(`Approved ${data.rules_created} rule(s) from ${selectedDoc?.filename}`);
      setCandidates([]);
      setSelectedCandidates(new Set());
      if (selectedDoc) selectDocument(selectedDoc.id);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Approval failed");
    }
  };

  // ---------------------------------------------------------------------------
  // Bulk selection
  // ---------------------------------------------------------------------------

  const toggleBulkMode = () => {
    if (bulkMode) {
      // Exit bulk mode
      setBulkMode(false);
      setBulkSelected(new Set());
      setBulkResults([]);
      setBulkApprovals(new Map());
    } else {
      // Enter bulk mode
      setBulkMode(true);
      setSelectedDoc(null);
      setLinkedRules([]);
      setCandidates([]);
      setExtractionId("");
    }
  };

  const toggleBulkDoc = (docId: string) => {
    setBulkSelected((prev) => {
      const next = new Set(prev);
      next.has(docId) ? next.delete(docId) : next.add(docId);
      return next;
    });
  };

  const selectAllDocs = () => {
    const unextractedIds = registeredDocs.map((d) => d.id);
    setBulkSelected(new Set(unextractedIds));
  };

  const deselectAllDocs = () => {
    setBulkSelected(new Set());
  };

  // ---------------------------------------------------------------------------
  // Bulk extraction — run extractions asynchronously (parallel with concurrency limit)
  // ---------------------------------------------------------------------------

  const runBulkExtraction = async () => {
    if (bulkSelected.size === 0) return;

    setBulkRunning(true);
    setMessage("");

    // Build initial results list
    const docs = registeredDocs.filter((d) => bulkSelected.has(d.id));
    const initial: BulkDocResult[] = docs.map((d) => ({
      docId: d.id,
      filename: d.filename,
      status: "extracting" as BulkDocStatus,
      candidates: [],
    }));
    setBulkResults([...initial]);

    // Extract a single document and update state as it completes
    const extractOne = async (index: number): Promise<void> => {
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/documents/${initial[index].docId}/extract`,
          { method: "POST" },
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const cands: Candidate[] = data.candidates ?? [];

        setBulkResults((prev) => {
          const next = [...prev];
          next[index] = {
            ...next[index],
            status: "done",
            extractionId: data.extraction_id,
            candidates: cands,
          };
          return next;
        });

        // Auto-select all candidates for this document
        if (cands.length > 0) {
          setBulkApprovals((prev) => {
            const next = new Map(prev);
            next.set(data.extraction_id, new Set(cands.map((c) => c.index)));
            return next;
          });
        }
      } catch (err) {
        setBulkResults((prev) => {
          const next = [...prev];
          next[index] = {
            ...next[index],
            status: "error",
            error: err instanceof Error ? err.message : "Unknown error",
          };
          return next;
        });
      }
    };

    // Run all extractions in parallel
    await Promise.all(initial.map((_, i) => extractOne(i)));

    setBulkRunning(false);

    // Compute summary from final state
    setBulkResults((prev) => {
      const completed = prev.filter((r) => r.status === "done").length;
      const failed = prev.filter((r) => r.status === "error").length;
      const totalCands = prev.reduce((s, r) => s + r.candidates.length, 0);
      setMessage(
        `Bulk extraction complete: ${completed} succeeded, ${failed} failed, ${totalCands} total candidates.`,
      );
      return prev;
    });
  };

  // ---------------------------------------------------------------------------
  // Bulk candidate toggle
  // ---------------------------------------------------------------------------

  const toggleBulkCandidate = (extractionId: string, index: number) => {
    setBulkApprovals((prev) => {
      const next = new Map(prev);
      const set = new Set(next.get(extractionId) ?? []);
      set.has(index) ? set.delete(index) : set.add(index);
      next.set(extractionId, set);
      return next;
    });
  };

  const selectAllBulkCandidates = (extractionId: string, indices: number[]) => {
    setBulkApprovals((prev) => {
      const next = new Map(prev);
      next.set(extractionId, new Set(indices));
      return next;
    });
  };

  const deselectAllBulkCandidates = (extractionId: string) => {
    setBulkApprovals((prev) => {
      const next = new Map(prev);
      next.set(extractionId, new Set());
      return next;
    });
  };

  // ---------------------------------------------------------------------------
  // Bulk approve — approve selected candidates across all extractions
  // ---------------------------------------------------------------------------

  const [bulkApproving, setBulkApproving] = useState(false);

  const runBulkApproval = async () => {
    // Collect extractions with selected candidates
    const toApprove = Array.from(bulkApprovals.entries()).filter(
      ([, indices]) => indices.size > 0,
    );
    if (toApprove.length === 0) return;

    setBulkApproving(true);
    let totalCreated = 0;
    let errors = 0;

    for (const [extId, indices] of toApprove) {
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/documents/extractions/${extId}/review`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              extraction_id: extId,
              approved_indices: Array.from(indices),
            }),
          },
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        totalCreated += data.rules_created ?? 0;
      } catch {
        errors++;
      }
    }

    setBulkApproving(false);
    setMessage(
      `Approved ${totalCreated} rule(s) from ${toApprove.length} document(s).` +
        (errors > 0 ? ` ${errors} approval(s) failed.` : ""),
    );
    setBulkResults([]);
    setBulkApprovals(new Map());
    setBulkSelected(new Set());
    setBulkMode(false);
    loadDocuments();
  };

  // ---------------------------------------------------------------------------
  // Computed values for bulk
  // ---------------------------------------------------------------------------

  const totalBulkCandidates = bulkResults.reduce(
    (sum, r) => sum + r.candidates.length,
    0,
  );
  const totalBulkSelected = Array.from(bulkApprovals.values()).reduce(
    (sum, s) => sum + s.size,
    0,
  );
  const bulkDoneCount = bulkResults.filter((r) => r.status === "done").length;
  const bulkErrorCount = bulkResults.filter((r) => r.status === "error").length;
  const bulkExtractingDoc = bulkResults.find((r) => r.status === "extracting");

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex gap-6">
      {/* Left panel: Document list */}
      <div className="w-80 shrink-0">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold" title="Upload policy documents and extract candidate rules via LLM analysis">Documents</h1>
          <button
            onClick={toggleBulkMode}
            disabled={bulkRunning}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              bulkMode
                ? "bg-gray-800 text-white hover:bg-gray-700"
                : "border border-gray-300 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {bulkMode ? "Exit Bulk" : "Bulk Extract"}
          </button>
        </div>

        {/* Upload zone */}
        <div
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={(e) => { e.preventDefault(); setDragging(false); }}
          onClick={() => fileInputRef.current?.click()}
          title="Drop PDF, text, or markdown files here to upload for rule extraction"
          className={`mb-4 flex cursor-pointer flex-col items-center rounded-lg border-2 border-dashed p-4 text-center transition-colors ${
            dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400"
          }`}
        >
          <p className="text-xs text-gray-500">
            {uploading ? uploadProgress : "Drop files or click to upload"}
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md"
            multiple
            onChange={handleFileInput}
            disabled={uploading}
            className="hidden"
          />
        </div>

        {message && (
          <p className="mb-3 rounded bg-blue-50 px-3 py-1.5 text-xs text-blue-800">{message}</p>
        )}

        {/* Bulk selection controls */}
        {bulkMode && (
          <div className="mb-3 flex items-center justify-between rounded-md bg-indigo-50 px-3 py-2">
            <span className="text-xs font-medium text-indigo-700">
              {bulkSelected.size} selected
            </span>
            <div className="flex gap-2">
              <button
                onClick={selectAllDocs}
                className="text-xs text-indigo-600 hover:underline"
              >
                All
              </button>
              <button
                onClick={deselectAllDocs}
                className="text-xs text-indigo-600 hover:underline"
              >
                None
              </button>
            </div>
          </div>
        )}

        {/* Document list */}
        <div className="space-y-1">
          {loadingDocs && <p className="text-xs text-gray-400">Loading...</p>}
          {!loadingDocs && registeredDocs.length === 0 && (
            <p className="text-xs text-gray-400">No documents uploaded yet.</p>
          )}
          {registeredDocs.map((doc) => (
            <div
              key={doc.id}
              className={`flex items-start gap-2 rounded-md border p-2.5 transition-colors ${
                bulkMode
                  ? bulkSelected.has(doc.id)
                    ? "border-indigo-400 bg-indigo-50"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                  : selectedDoc?.id === doc.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              {bulkMode && (
                <input
                  type="checkbox"
                  checked={bulkSelected.has(doc.id)}
                  onChange={() => toggleBulkDoc(doc.id)}
                  disabled={bulkRunning}
                  className="mt-1 accent-indigo-600"
                />
              )}
              <button
                onClick={() =>
                  bulkMode ? toggleBulkDoc(doc.id) : selectDocument(doc.id)
                }
                disabled={bulkRunning}
                className="min-w-0 flex-1 text-left"
              >
                <p className="truncate text-sm font-medium">{doc.filename}</p>
                <p className="text-xs text-gray-400">
                  {(doc.size_bytes / 1024).toFixed(1)} KB &middot;{" "}
                  {new Date(doc.uploaded_at).toLocaleDateString()}
                </p>
              </button>
            </div>
          ))}
        </div>
        {totalDocs > registeredDocs.length && (
          <p className="mt-2 text-xs text-gray-400">
            Showing {registeredDocs.length} of {totalDocs}
          </p>
        )}

        {/* Bulk extract button at bottom of left panel */}
        {bulkMode && bulkSelected.size > 0 && bulkResults.length === 0 && (
          <button
            onClick={runBulkExtraction}
            disabled={bulkRunning}
            className="mt-4 w-full rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {bulkRunning
              ? "Extracting..."
              : `Extract from ${bulkSelected.size} Document${bulkSelected.size !== 1 ? "s" : ""}`}
          </button>
        )}
      </div>

      {/* Right panel */}
      <div className="min-w-0 flex-1">
        {/* ================================================================ */}
        {/* BULK EXTRACTION PANEL                                            */}
        {/* ================================================================ */}
        {bulkMode && (
          <div className="space-y-6">
            {/* No docs selected and no results yet */}
            {bulkSelected.size === 0 && bulkResults.length === 0 && (
              <div className="flex h-64 items-center justify-center text-gray-400">
                Select documents from the list, then click &ldquo;Extract&rdquo;
              </div>
            )}

            {/* Docs selected but not yet started */}
            {bulkSelected.size > 0 && bulkResults.length === 0 && (
              <div className="rounded-lg border bg-white p-6">
                <h2 className="mb-3 text-lg font-bold">
                  Bulk Rule Extraction
                </h2>
                <p className="mb-4 text-sm text-gray-600">
                  {bulkSelected.size} document{bulkSelected.size !== 1 ? "s" : ""} selected
                  for extraction. The LLM will analyze each document and propose
                  candidate rules.
                </p>
                <div className="space-y-1">
                  {registeredDocs
                    .filter((d) => bulkSelected.has(d.id))
                    .map((d) => (
                      <div
                        key={d.id}
                        className="flex items-center justify-between rounded-md bg-gray-50 px-3 py-2"
                      >
                        <span className="truncate text-sm">{d.filename}</span>
                        <span className="text-xs text-gray-400">
                          {(d.size_bytes / 1024).toFixed(1)} KB
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Progress / Results */}
            {bulkResults.length > 0 && (
              <>
                {/* Progress header */}
                <div className="rounded-lg border bg-white p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-bold">
                      {bulkRunning ? "Extracting..." : "Extraction Results"}
                    </h2>
                    <div className="flex items-center gap-3 text-sm">
                      {bulkRunning && bulkExtractingDoc && (
                        <span className="text-indigo-600">
                          Processing: {bulkExtractingDoc.filename}
                        </span>
                      )}
                      <span className="text-gray-500">
                        {bulkDoneCount}/{bulkResults.length} done
                        {bulkErrorCount > 0 && (
                          <span className="ml-1 text-red-500">
                            ({bulkErrorCount} failed)
                          </span>
                        )}
                      </span>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="mb-3 h-2 overflow-hidden rounded-full bg-gray-100">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        bulkRunning ? "bg-indigo-500" : "bg-green-500"
                      }`}
                      style={{
                        width: `${((bulkDoneCount + bulkErrorCount) / Math.max(bulkResults.length, 1)) * 100}%`,
                      }}
                    />
                  </div>

                  {/* Per-document status list */}
                  <div className="space-y-1">
                    {bulkResults.map((r) => (
                      <div
                        key={r.docId}
                        className="flex items-center justify-between rounded px-3 py-1.5 text-sm"
                      >
                        <span className="truncate">{r.filename}</span>
                        <span className="flex items-center gap-2">
                          {r.status === "pending" && (
                            <span className="text-gray-400">Waiting</span>
                          )}
                          {r.status === "extracting" && (
                            <span className="flex items-center gap-1 text-indigo-600">
                              <svg
                                className="h-3 w-3 animate-spin"
                                viewBox="0 0 24 24"
                                fill="none"
                              >
                                <circle
                                  cx="12"
                                  cy="12"
                                  r="10"
                                  stroke="currentColor"
                                  strokeWidth="4"
                                  className="opacity-25"
                                />
                                <path
                                  fill="currentColor"
                                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                                  className="opacity-75"
                                />
                              </svg>
                              Extracting
                            </span>
                          )}
                          {r.status === "done" && (
                            <span className="text-green-600">
                              {r.candidates.length} candidate{r.candidates.length !== 1 ? "s" : ""}
                            </span>
                          )}
                          {r.status === "error" && (
                            <span className="text-red-500" title={r.error}>
                              Failed
                            </span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Bulk candidates review (only after extraction is done) */}
                {!bulkRunning && totalBulkCandidates > 0 && (
                  <div className="space-y-4">
                    {/* Bulk approval header */}
                    <div className="flex items-center justify-between rounded-lg border bg-white px-4 py-3">
                      <div>
                        <h3 className="text-sm font-medium">
                          {totalBulkCandidates} candidate{totalBulkCandidates !== 1 ? "s" : ""} from{" "}
                          {bulkResults.filter((r) => r.candidates.length > 0).length} document{bulkResults.filter((r) => r.candidates.length > 0).length !== 1 ? "s" : ""}
                        </h3>
                        <p className="text-xs text-gray-500">
                          {totalBulkSelected} selected for approval
                        </p>
                      </div>
                      <button
                        onClick={runBulkApproval}
                        disabled={bulkApproving || totalBulkSelected === 0}
                        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        {bulkApproving
                          ? "Approving..."
                          : `Approve All (${totalBulkSelected})`}
                      </button>
                    </div>

                    {/* Per-document candidates */}
                    {bulkResults
                      .filter((r) => r.status === "done" && r.candidates.length > 0)
                      .map((r) => {
                        const selected = bulkApprovals.get(r.extractionId!) ?? new Set<number>();
                        const allIndices = r.candidates.map((c) => c.index);
                        const allSelected = allIndices.every((i) => selected.has(i));

                        return (
                          <div key={r.docId} className="rounded-lg border bg-white">
                            {/* Document header */}
                            <div className="flex items-center justify-between border-b px-4 py-3">
                              <div>
                                <h4 className="text-sm font-medium">{r.filename}</h4>
                                <p className="text-xs text-gray-400">
                                  {r.candidates.length} candidate{r.candidates.length !== 1 ? "s" : ""} &middot;{" "}
                                  {selected.size} selected
                                </p>
                              </div>
                              <div className="flex gap-2">
                                <button
                                  onClick={() =>
                                    allSelected
                                      ? deselectAllBulkCandidates(r.extractionId!)
                                      : selectAllBulkCandidates(r.extractionId!, allIndices)
                                  }
                                  className="rounded border px-2 py-1 text-xs hover:bg-gray-50"
                                >
                                  {allSelected ? "Deselect All" : "Select All"}
                                </button>
                              </div>
                            </div>

                            {/* Candidate list */}
                            <div className="space-y-1 p-3">
                              {r.candidates.map((c) => (
                                <label
                                  key={`${r.extractionId}-${c.index}`}
                                  className={`flex cursor-pointer items-start gap-2 rounded-md border p-2.5 ${
                                    selected.has(c.index)
                                      ? "border-blue-400 bg-blue-50"
                                      : "border-gray-200 hover:bg-gray-50"
                                  }`}
                                >
                                  <input
                                    type="checkbox"
                                    checked={selected.has(c.index)}
                                    onChange={() =>
                                      toggleBulkCandidate(r.extractionId!, c.index)
                                    }
                                    className="mt-0.5"
                                  />
                                  <div className="min-w-0 flex-1">
                                    <p className="text-sm">{c.statement}</p>
                                    <div className="mt-1 flex gap-1.5 text-xs">
                                      <Badge label={c.modality} variant="modality" />
                                      <Badge label={c.severity} variant="severity" />
                                      <span className="text-gray-400">
                                        {(c.confidence * 100).toFixed(0)}% confidence
                                      </span>
                                    </div>
                                  </div>
                                </label>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ================================================================ */}
        {/* SINGLE DOCUMENT DETAIL PANEL (existing behavior)                 */}
        {/* ================================================================ */}
        {!bulkMode && (
          <>
            {!selectedDoc && !loadingDetail && (
              <div className="flex h-64 items-center justify-center text-gray-400">
                Select a document to view its content and extracted rules
              </div>
            )}

            {loadingDetail && (
              <div className="flex h-64 items-center justify-center text-gray-400">
                Loading...
              </div>
            )}

            {selectedDoc && !loadingDetail && (
              <div className="space-y-6">
                {/* Document header */}
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-xl font-bold">{selectedDoc.filename}</h2>
                    <p className="text-sm text-gray-500">
                      {selectedDoc.mime_type} &middot; {(selectedDoc.size_bytes / 1024).toFixed(1)} KB
                      &middot; Uploaded {new Date(selectedDoc.uploaded_at).toLocaleString()}
                      &middot; by {selectedDoc.uploaded_by}
                    </p>
                    <p className="mt-1 font-mono text-xs text-gray-400">{selectedDoc.id}</p>
                  </div>
                  {linkedRules.length > 0 ? (
                    <span className="rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-500">
                      {linkedRules.length} rule{linkedRules.length !== 1 ? "s" : ""} extracted
                    </span>
                  ) : (
                    <button
                      onClick={handleExtract}
                      disabled={extracting}
                      title="Run LLM-powered extraction to discover candidate rules in this document"
                      className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                    >
                      {extracting ? "Extracting..." : "Extract Rules"}
                    </button>
                  )}
                </div>

                {/* Linked rules (toggle) */}
                {linkedRules.length > 0 && (
                  <div className="rounded-lg border bg-white">
                    <button
                      onClick={() => setShowRules((v) => !v)}
                      className="flex w-full items-center justify-between p-4 text-left hover:bg-gray-50"
                    >
                      <h3 className="text-sm font-medium uppercase text-gray-500">
                        Rules from this Document ({linkedRules.length})
                      </h3>
                      <svg
                        className={`h-4 w-4 text-gray-400 transition-transform ${showRules ? "rotate-180" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {showRules && (
                      <div className="space-y-2 px-4 pb-4">
                        {linkedRules.map((item) => (
                          <div key={item.rule.id} className="rounded-md border p-3">
                            <a href={`/rules/${item.rule.id}`} className="text-sm text-blue-600 hover:underline">
                              {item.rule.statement}
                            </a>
                            <div className="mt-1.5 flex gap-1.5">
                              <Badge label={item.rule.modality} variant="modality" />
                              <Badge label={item.rule.severity} variant="severity" />
                              <Badge label={item.rule.status} variant="status" />
                              {item.rule.tags.slice(0, 3).map((t) => (
                                <Badge key={t} label={t} variant="tag" />
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {linkedRules.length === 0 && !candidates.length && (
                  <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-500">
                    No rules have been extracted from this document yet. Click &ldquo;Extract Rules&rdquo; to analyze.
                  </div>
                )}

                {/* Extraction candidates (if just extracted) */}
                {candidates.length > 0 && (
                  <div className="rounded-lg border bg-white p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-sm font-medium uppercase text-gray-500">
                        Candidates ({candidates.length})
                      </h3>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setSelectedCandidates(new Set(candidates.map((c) => c.index)))}
                          className="rounded border px-2 py-1 text-xs hover:bg-gray-50"
                        >
                          Select All
                        </button>
                        <button
                          onClick={handleApprove}
                          disabled={selectedCandidates.size === 0}
                          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                          Approve ({selectedCandidates.size})
                        </button>
                      </div>
                    </div>
                    <div className="space-y-2">
                      {candidates.map((c) => (
                        <label
                          key={c.index}
                          className={`flex cursor-pointer items-start gap-2 rounded-md border p-3 ${
                            selectedCandidates.has(c.index) ? "border-blue-500 bg-blue-50" : "hover:bg-gray-50"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedCandidates.has(c.index)}
                            onChange={() => {
                              setSelectedCandidates((prev) => {
                                const next = new Set(prev);
                                next.has(c.index) ? next.delete(c.index) : next.add(c.index);
                                return next;
                              });
                            }}
                            className="mt-0.5"
                          />
                          <div className="flex-1">
                            <p className="text-sm">{c.statement}</p>
                            <div className="mt-1 flex gap-1.5 text-xs">
                              <Badge label={c.modality} variant="modality" />
                              <Badge label={c.severity} variant="severity" />
                              <span className="text-gray-400">
                                {(c.confidence * 100).toFixed(0)}% confidence
                              </span>
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {/* Document content */}
                {selectedDoc.content_text && (
                  <div className="rounded-lg border bg-white p-4">
                    <h3 className="mb-3 text-sm font-medium uppercase text-gray-500">
                      Document Content
                    </h3>
                    <pre className="max-h-[500px] overflow-auto whitespace-pre-wrap rounded-md bg-gray-50 p-4 font-mono text-xs leading-relaxed text-gray-700">
                      {selectedDoc.content_text}
                    </pre>
                  </div>
                )}

                {!selectedDoc.content_text && (
                  <div className="rounded-lg border bg-gray-50 p-4 text-center text-sm text-gray-400">
                    Content preview not available for {selectedDoc.mime_type} files.
                  </div>
                )}

                {/* Extraction history */}
                {selectedDoc.extractions.length > 0 && (
                  <div className="rounded-lg border bg-white p-4">
                    <h3 className="mb-3 text-sm font-medium uppercase text-gray-500">
                      Extraction History
                    </h3>
                    <div className="space-y-1.5">
                      {selectedDoc.extractions.map((ext) => (
                        <div key={ext.id} className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">
                            {new Date(ext.extracted_at).toLocaleString()} &middot; {ext.model_id}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400">{ext.candidates_count} candidates</span>
                            <Badge
                              label={ext.status}
                              variant={ext.status === "REVIEWED" ? "status" : "tag"}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
