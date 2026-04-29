"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Badge from "@/components/Badge";

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

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DocumentsPage() {
  // --- Registered documents list ---
  const [registeredDocs, setRegisteredDocs] = useState<DocSummary[]>([]);
  const [totalDocs, setTotalDocs] = useState(0);
  const [loadingDocs, setLoadingDocs] = useState(true);

  // --- Detail view ---
  const [selectedDoc, setSelectedDoc] = useState<DocDetail | null>(null);
  const [linkedRules, setLinkedRules] = useState<LinkedRule[]>([]);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // --- Upload ---
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [dragging, setDragging] = useState(false);
  const [message, setMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Extraction ---
  const [extracting, setExtracting] = useState(false);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [extractionId, setExtractionId] = useState("");
  const [selectedCandidates, setSelectedCandidates] = useState<Set<number>>(new Set());

  // --- Toggles ---
  const [showRules, setShowRules] = useState(true);

  // ---------------------------------------------------------------------------
  // Load registered documents on mount
  // ---------------------------------------------------------------------------

  const loadDocuments = useCallback(async () => {
    setLoadingDocs(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/documents?page=1&page_size=100`);
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
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // ---------------------------------------------------------------------------
  // Select a document → load detail + linked rules
  // ---------------------------------------------------------------------------

  const selectDocument = async (docId: string) => {
    setLoadingDetail(true);
    setSelectedDoc(null);
    setLinkedRules([]);
    setCandidates([]);
    setExtractionId("");
    setSelectedCandidates(new Set());

    try {
      // Fetch detail (includes content_text and extractions)
      const detailRes = await fetch(`${API_BASE}/api/v1/documents/${docId}`);
      if (!detailRes.ok) throw new Error("Failed to load document");
      const detail: DocDetail = await detailRes.json();
      setSelectedDoc(detail);

      // Fetch rules linked to this document
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
          const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
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
      loadDocuments(); // refresh list
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
  // Extract rules from selected document
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
      // Refresh linked rules
      if (selectedDoc) selectDocument(selectedDoc.id);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Approval failed");
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex gap-6">
      {/* Left panel: Document list */}
      <div className="w-80 shrink-0">
        <h1 className="mb-4 text-2xl font-bold">Documents</h1>

        {/* Upload zone */}
        <div
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={(e) => { e.preventDefault(); setDragging(false); }}
          onClick={() => fileInputRef.current?.click()}
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

        {/* Document list */}
        <div className="space-y-1">
          {loadingDocs && <p className="text-xs text-gray-400">Loading...</p>}
          {!loadingDocs && registeredDocs.length === 0 && (
            <p className="text-xs text-gray-400">No documents uploaded yet.</p>
          )}
          {registeredDocs.map((doc) => (
            <button
              key={doc.id}
              onClick={() => selectDocument(doc.id)}
              className={`w-full rounded-md border p-2.5 text-left transition-colors ${
                selectedDoc?.id === doc.id
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              <p className="truncate text-sm font-medium">{doc.filename}</p>
              <p className="text-xs text-gray-400">
                {(doc.size_bytes / 1024).toFixed(1)} KB &middot;{" "}
                {new Date(doc.uploaded_at).toLocaleDateString()}
              </p>
            </button>
          ))}
        </div>
        {totalDocs > registeredDocs.length && (
          <p className="mt-2 text-xs text-gray-400">
            Showing {registeredDocs.length} of {totalDocs}
          </p>
        )}
      </div>

      {/* Right panel: Detail view */}
      <div className="min-w-0 flex-1">
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
      </div>
    </div>
  );
}
