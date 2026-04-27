"use client";

import { useState } from "react";
import { type PlaygroundResult, playgroundEvaluate } from "@/lib/api";

const MODALITY_OPTIONS = ["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"] as const;
const SEVERITY_OPTIONS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

function VerdictBadge({ verdict }: { verdict: string }) {
  const colorMap: Record<string, string> = {
    ALLOW: "bg-green-100 text-green-800 border-green-300",
    DENY: "bg-red-100 text-red-800 border-red-300",
    NEEDS_CONFIRMATION: "bg-yellow-100 text-yellow-800 border-yellow-300",
  };
  const classes = colorMap[verdict] ?? "bg-gray-100 text-gray-800 border-gray-300";
  return (
    <span className={`inline-block rounded-full border px-4 py-1.5 text-sm font-semibold ${classes}`}>
      {verdict}
    </span>
  );
}

export default function PlaygroundPage() {
  const [statement, setStatement] = useState("");
  const [modality, setModality] = useState<string>("MUST");
  const [severity, setSeverity] = useState<string>("MEDIUM");
  const [sampleCode, setSampleCode] = useState("");
  const [result, setResult] = useState<PlaygroundResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleEvaluate = async () => {
    if (!statement.trim()) {
      setError("Rule statement is required.");
      return;
    }
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const res = await playgroundEvaluate({
        rule_statement: statement,
        rule_modality: modality,
        rule_severity: severity,
        sample_code: sampleCode || undefined,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Rule Playground</h1>
        <p className="mt-1 text-sm text-gray-500">
          Test rules against sample code before deploying
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Left panel: Rule editor */}
        <div className="space-y-4 rounded-lg border bg-white p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Rule Definition
          </h2>
          <div>
            <label htmlFor="statement" className="mb-1 block text-sm font-medium text-gray-700">
              Statement
            </label>
            <textarea
              id="statement"
              rows={6}
              className="w-full rounded-md border px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="e.g. All exported functions MUST have a JSDoc comment."
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
            />
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <label htmlFor="modality" className="mb-1 block text-sm font-medium text-gray-700">
                Modality
              </label>
              <select
                id="modality"
                className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={modality}
                onChange={(e) => setModality(e.target.value)}
              >
                {MODALITY_OPTIONS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label htmlFor="severity" className="mb-1 block text-sm font-medium text-gray-700">
                Severity
              </label>
              <select
                id="severity"
                className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
              >
                {SEVERITY_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Right panel: Sample code */}
        <div className="space-y-4 rounded-lg border bg-white p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Sample Code
          </h2>
          <textarea
            rows={10}
            className="w-full flex-1 rounded-md border px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Paste sample code here..."
            value={sampleCode}
            onChange={(e) => setSampleCode(e.target.value)}
          />
        </div>
      </div>

      <div className="flex justify-center">
        <button
          onClick={handleEvaluate}
          disabled={loading}
          className="rounded-md bg-blue-600 px-8 py-2.5 text-sm font-semibold text-white shadow hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Evaluating..." : "Evaluate"}
        </button>
      </div>

      {/* Result panel */}
      {result && (
        <div className="space-y-4 rounded-lg border bg-white p-6">
          <div className="flex items-center gap-4">
            <VerdictBadge verdict={result.verdict} />
            <span className="text-sm text-gray-600">
              Confidence: <span className="font-semibold">{(result.confidence * 100).toFixed(0)}%</span>
            </span>
          </div>

          {result.issue_description && (
            <div>
              <h3 className="mb-1 text-sm font-semibold text-gray-700">Issue</h3>
              <p className="text-sm text-gray-600">{result.issue_description}</p>
            </div>
          )}

          <div>
            <h3 className="mb-1 text-sm font-semibold text-gray-700">Reasoning</h3>
            <p className="whitespace-pre-wrap rounded-md bg-gray-50 p-3 text-sm text-gray-600">
              {result.reasoning}
            </p>
          </div>

          {result.fix_suggestion && (
            <div className="rounded-md border border-blue-200 bg-blue-50 p-4">
              <h3 className="mb-1 text-sm font-semibold text-blue-800">Fix Suggestion</h3>
              <p className="text-sm text-blue-700">{result.fix_suggestion}</p>
            </div>
          )}

          {result.locations.length > 0 && (
            <div>
              <h3 className="mb-1 text-sm font-semibold text-gray-700">Locations</h3>
              <ul className="space-y-1">
                {result.locations.map((loc, i) => (
                  <li key={i} className="text-sm text-gray-600">
                    <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">
                      {loc.file_path}
                      {loc.start_line != null && `:${loc.start_line}`}
                    </code>
                    {loc.function_name && (
                      <span className="ml-2 text-gray-400">({loc.function_name})</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
