"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface Candidate {
  index: number;
  statement: string;
  modality: string;
  severity: string;
  confidence: number;
  scope: string[];
  tags: string[];
}

export default function DocumentsPage() {
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [documentId, setDocumentId] = useState("");
  const [extractionId, setExtractionId] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
    new Set(),
  );
  const [message, setMessage] = useState("");

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setMessage("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      const data = await res.json();
      setDocumentId(data.document_id);
      setMessage(`Uploaded: ${data.filename} (${data.size_bytes} bytes)`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleExtract = async () => {
    if (!documentId) return;
    setExtracting(true);
    setMessage("");
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/documents/${documentId}/extract`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error(`Extraction failed: ${res.status}`);
      const data = await res.json();
      setExtractionId(data.extraction_id);
      setCandidates(data.candidates ?? []);
      setMessage(`Extracted ${data.candidates?.length ?? 0} candidate rules`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Extraction failed");
    } finally {
      setExtracting(false);
    }
  };

  const toggleCandidate = (index: number) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const handleApprove = async () => {
    if (!extractionId || selectedIndices.size === 0) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/documents/extractions/${extractionId}/review`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            extraction_id: extractionId,
            approved_indices: Array.from(selectedIndices),
          }),
        },
      );
      if (!res.ok) throw new Error(`Review failed: ${res.status}`);
      const data = await res.json();
      setMessage(
        `Approved ${data.rules_created} rules. IDs: ${data.rule_ids?.join(", ")}`,
      );
      setCandidates([]);
      setSelectedIndices(new Set());
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Review failed");
    }
  };

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Documents &amp; Extraction</h1>

      {/* Upload */}
      <div className="mb-8 rounded-lg border bg-white p-6">
        <h2 className="mb-3 text-lg font-medium">Upload Document</h2>
        <input
          type="file"
          accept=".pdf,.txt,.md"
          onChange={handleUpload}
          disabled={uploading}
          className="text-sm"
        />
        {uploading && <p className="mt-2 text-sm text-gray-500">Uploading...</p>}

        {documentId && (
          <div className="mt-4">
            <p className="text-sm text-gray-600">
              Document ID: <code className="font-mono text-xs">{documentId}</code>
            </p>
            <button
              onClick={handleExtract}
              disabled={extracting}
              className="mt-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {extracting ? "Extracting..." : "Extract Rules"}
            </button>
          </div>
        )}
      </div>

      {message && (
        <p className="mb-4 rounded bg-blue-50 px-4 py-2 text-sm text-blue-800">
          {message}
        </p>
      )}

      {/* Candidates */}
      {candidates.length > 0 && (
        <div className="rounded-lg border bg-white p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-medium">
              Candidate Rules ({candidates.length})
            </h2>
            <button
              onClick={handleApprove}
              disabled={selectedIndices.size === 0}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Approve Selected ({selectedIndices.size})
            </button>
          </div>
          <div className="space-y-3">
            {candidates.map((c) => (
              <label
                key={c.index}
                className={`flex cursor-pointer items-start gap-3 rounded-md border p-4 ${
                  selectedIndices.has(c.index)
                    ? "border-blue-500 bg-blue-50"
                    : "hover:bg-gray-50"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedIndices.has(c.index)}
                  onChange={() => toggleCandidate(c.index)}
                  className="mt-1"
                />
                <div className="flex-1">
                  <p className="text-sm">{c.statement}</p>
                  <div className="mt-1 flex gap-2 text-xs">
                    <span className="rounded bg-blue-100 px-1.5 py-0.5 text-blue-800">
                      {c.modality}
                    </span>
                    <span className="rounded bg-orange-100 px-1.5 py-0.5 text-orange-800">
                      {c.severity}
                    </span>
                    <span className="text-gray-500">
                      confidence: {(c.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
