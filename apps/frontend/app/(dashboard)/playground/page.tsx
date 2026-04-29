"use client";

import { useState, useCallback } from "react";
import { type PlaygroundResult, playgroundEvaluate } from "@/lib/api";

/* ---------- Constants ---------- */

const MODALITY_OPTIONS = ["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"] as const;
const SEVERITY_OPTIONS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

type InputMode = "code" | "scenario";

interface FactEntry {
  key: string;
  value: string;
}

/* ---------- Sub-components ---------- */

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

function TabButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
        active
          ? "bg-blue-600 text-white"
          : "border border-gray-300 text-gray-600 hover:bg-gray-50"
      }`}
    >
      {label}
    </button>
  );
}

/* ---------- Main Component ---------- */

export default function PlaygroundPage() {
  // Rule definition
  const [statement, setStatement] = useState("");
  const [modality, setModality] = useState<string>("MUST");
  const [severity, setSeverity] = useState<string>("MEDIUM");

  // Input mode
  const [inputMode, setInputMode] = useState<InputMode>("code");

  // Code mode state
  const [sampleCode, setSampleCode] = useState("");

  // Scenario mode state
  const [narrative, setNarrative] = useState("");
  const [facts, setFacts] = useState<FactEntry[]>([]);

  // Result
  const [result, setResult] = useState<PlaygroundResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  /* ---- Facts management ---- */

  const addFact = useCallback(() => {
    setFacts((prev) => [...prev, { key: "", value: "" }]);
  }, []);

  const removeFact = useCallback((index: number) => {
    setFacts((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateFact = useCallback(
    (index: number, field: "key" | "value", val: string) => {
      setFacts((prev) => prev.map((f, i) => (i === index ? { ...f, [field]: val } : f)));
    },
    [],
  );

  /* ---- Evaluate ---- */

  const handleEvaluate = async () => {
    if (!statement.trim()) {
      setError("Rule statement is required.");
      return;
    }

    setError("");
    setResult(null);
    setLoading(true);

    try {
      if (inputMode === "code") {
        const res = await playgroundEvaluate({
          rule_statement: statement,
          rule_modality: modality,
          rule_severity: severity,
          sample_code: sampleCode || undefined,
        });
        setResult(res);
      } else {
        // Build sample_facts from narrative + structured facts
        const sampleFacts: Record<string, unknown> = {};
        if (narrative.trim()) {
          sampleFacts.narrative = narrative.trim();
        }
        for (const f of facts) {
          if (f.key.trim()) {
            sampleFacts[f.key.trim()] = f.value.trim();
          }
        }

        const res = await playgroundEvaluate({
          rule_statement: statement,
          rule_modality: modality,
          rule_severity: severity,
          sample_facts: Object.keys(sampleFacts).length > 0 ? sampleFacts : undefined,
        });
        setResult(res);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  /* ---- Render ---- */

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Rule Playground</h1>
        <p className="mt-1 text-sm text-gray-500">
          Test rules against code changes or real-world scenarios before deploying
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* ============ Left panel: Rule Definition ============ */}
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
              placeholder={
                inputMode === "code"
                  ? "e.g. All exported functions MUST have a JSDoc comment."
                  : "e.g. Monthly overtime MUST NOT exceed 45 hours without prior 36-agreement filing."
              }
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

        {/* ============ Right panel: Input ============ */}
        <div className="space-y-4 rounded-lg border bg-white p-5">
          {/* Mode tabs */}
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
              Test Input
            </h2>
            <div className="flex gap-2">
              <TabButton
                active={inputMode === "code"}
                label="Code"
                onClick={() => setInputMode("code")}
              />
              <TabButton
                active={inputMode === "scenario"}
                label="Scenario"
                onClick={() => setInputMode("scenario")}
              />
            </div>
          </div>

          {/* Code mode */}
          {inputMode === "code" && (
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Code snippet or unified diff
              </label>
              <textarea
                rows={12}
                className="w-full rounded-md border px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Paste code or diff here..."
                value={sampleCode}
                onChange={(e) => setSampleCode(e.target.value)}
              />
            </div>
          )}

          {/* Scenario mode */}
          {inputMode === "scenario" && (
            <div className="space-y-4">
              {/* Narrative */}
              <div>
                <label className="mb-1 block text-xs text-gray-500">
                  Describe the situation
                </label>
                <textarea
                  rows={5}
                  className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="e.g. Employee John (ID: E001) submitted 52 hours of overtime for April 2026. No 36-agreement has been filed for this period."
                  value={narrative}
                  onChange={(e) => setNarrative(e.target.value)}
                />
              </div>

              {/* Structured facts */}
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label className="text-xs text-gray-500">
                    Structured facts <span className="text-gray-400">(optional)</span>
                  </label>
                  <button
                    onClick={addFact}
                    className="rounded border px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50"
                  >
                    + Add fact
                  </button>
                </div>

                {facts.length === 0 ? (
                  <p className="rounded-md border border-dashed px-3 py-3 text-center text-xs text-gray-400">
                    No structured facts added. Click &quot;+ Add fact&quot; to add key-value pairs
                    like <span className="font-mono">overtime_hours: 52</span>.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {facts.map((f, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <input
                          type="text"
                          className="w-1/3 rounded-md border px-2 py-1.5 font-mono text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          placeholder="key"
                          value={f.key}
                          onChange={(e) => updateFact(i, "key", e.target.value)}
                        />
                        <span className="text-gray-400">:</span>
                        <input
                          type="text"
                          className="flex-1 rounded-md border px-2 py-1.5 font-mono text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          placeholder="value"
                          value={f.value}
                          onChange={(e) => updateFact(i, "value", e.target.value)}
                        />
                        <button
                          onClick={() => removeFact(i)}
                          className="flex-shrink-0 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
                          title="Remove fact"
                        >
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ============ Evaluate button ============ */}
      <div className="flex justify-center">
        <button
          onClick={handleEvaluate}
          disabled={loading}
          className="rounded-md bg-blue-600 px-8 py-2.5 text-sm font-semibold text-white shadow hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Evaluating..." : "Evaluate"}
        </button>
      </div>

      {/* ============ Result panel ============ */}
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
