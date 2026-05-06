"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  type PlaygroundResult,
  type Rule,
  type RuleList,
  type SuggestInputResult,
  playgroundEvaluate,
  suggestInput,
} from "@/lib/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/* ---------- Constants ---------- */

const MODALITY_OPTIONS = ["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"] as const;
const SEVERITY_OPTIONS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

type InputMode = "code" | "scenario";
type RuleSource = "manual" | "existing";

interface FactEntry {
  key: string;
  value: string;
}

interface SelectedRule {
  id: string;
  statement: string;
  modality: string;
  severity: string;
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

/* ---------- Rule Search Dropdown ---------- */

function RuleSearchPicker({
  selectedRules,
  onAdd,
  onRemove,
}: {
  selectedRules: SelectedRule[];
  onAdd: (rule: SelectedRule) => void;
  onRemove: (ruleId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Rule[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const selectedIds = new Set(selectedRules.map((r) => r.id));

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      // Load first page of rules when query is empty
      setSearching(true);
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/rules?page=1&page_size=20`,
        );
        if (res.ok) {
          const data: RuleList = await res.json();
          setSearchResults(data.items);
        }
      } catch {
        // ignore
      } finally {
        setSearching(false);
      }
      return;
    }

    setSearching(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/search/fulltext`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, page: 1, page_size: 20 }),
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(
          (data.items ?? []).map((item: { rule: Rule }) => item.rule ?? item),
        );
      }
    } catch {
      // ignore
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    if (!showDropdown) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(query), 300);
    return () => clearTimeout(debounceRef.current);
  }, [query, showDropdown, doSearch]);

  // Close dropdown on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="space-y-3">
      {/* Selected rules chips */}
      {selectedRules.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedRules.map((rule) => (
            <div
              key={rule.id}
              className="flex items-center gap-1.5 rounded-md border bg-blue-50 px-2.5 py-1.5"
            >
              <span className="max-w-[280px] truncate text-xs">
                {rule.statement}
              </span>
              <span className="rounded bg-blue-200 px-1 py-0.5 text-[10px] font-medium text-blue-800">
                {rule.modality}
              </span>
              <button
                onClick={() => onRemove(rule.id)}
                className="ml-0.5 text-gray-400 hover:text-red-500"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Search input */}
      <div ref={dropdownRef} className="relative">
        <input
          type="text"
          className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Search rules by keyword..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            setShowDropdown(true);
            if (searchResults.length === 0) doSearch(query);
          }}
        />

        {showDropdown && (
          <div className="absolute z-10 mt-1 max-h-64 w-full overflow-auto rounded-md border bg-white shadow-lg">
            {searching && (
              <div className="px-3 py-2 text-xs text-gray-400">Searching...</div>
            )}
            {!searching && searchResults.length === 0 && (
              <div className="px-3 py-2 text-xs text-gray-400">
                {query ? "No rules found" : "No rules available"}
              </div>
            )}
            {searchResults.map((rule) => {
              const alreadySelected = selectedIds.has(rule.id);
              return (
                <button
                  key={rule.id}
                  disabled={alreadySelected}
                  onClick={() => {
                    onAdd({
                      id: rule.id,
                      statement: rule.statement,
                      modality: rule.modality,
                      severity: rule.severity,
                    });
                    setQuery("");
                    setShowDropdown(false);
                  }}
                  className={`flex w-full items-start gap-2 border-b px-3 py-2.5 text-left last:border-b-0 ${
                    alreadySelected
                      ? "cursor-not-allowed bg-gray-50 opacity-50"
                      : "hover:bg-blue-50"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm">
                      {rule.statement.length > 120
                        ? `${rule.statement.slice(0, 120)}...`
                        : rule.statement}
                    </p>
                    <div className="mt-1 flex gap-1.5">
                      <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium">
                        {rule.modality}
                      </span>
                      <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium">
                        {rule.severity}
                      </span>
                    </div>
                  </div>
                  {alreadySelected && (
                    <span className="mt-1 text-xs text-green-600">Added</span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------- Main Component ---------- */

export default function PlaygroundPage() {
  // Rule source
  const [ruleSource, setRuleSource] = useState<RuleSource>("existing");

  // Manual rule definition
  const [statement, setStatement] = useState("");
  const [modality, setModality] = useState<string>("MUST");
  const [severity, setSeverity] = useState<string>("MEDIUM");

  // Selected existing rules
  const [selectedRules, setSelectedRules] = useState<SelectedRule[]>([]);

  // Input mode
  const [inputMode, setInputMode] = useState<InputMode>("code");

  // Code mode state
  const [sampleCode, setSampleCode] = useState("");

  // Scenario mode state
  const [narrative, setNarrative] = useState("");
  const [facts, setFacts] = useState<FactEntry[]>([]);

  // Result — now array for multi-rule
  const [results, setResults] = useState<
    Array<{ rule: SelectedRule; result: PlaygroundResult }>
  >([]);
  const [singleResult, setSingleResult] = useState<PlaygroundResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Suggest by LLM
  const [suggesting, setSuggesting] = useState(false);
  const [suggestDescription, setSuggestDescription] = useState("");

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

  /* ---- Rule selection ---- */

  const addRule = (rule: SelectedRule) => {
    setSelectedRules((prev) => [...prev, rule]);
  };

  const removeRule = (ruleId: string) => {
    setSelectedRules((prev) => prev.filter((r) => r.id !== ruleId));
  };

  /* ---- Build input payload ---- */

  const buildInput = () => {
    if (inputMode === "code") {
      return { sample_code: sampleCode || undefined };
    }
    const sampleFacts: Record<string, unknown> = {};
    if (narrative.trim()) sampleFacts.narrative = narrative.trim();
    for (const f of facts) {
      if (f.key.trim()) sampleFacts[f.key.trim()] = f.value.trim();
    }
    return {
      sample_facts: Object.keys(sampleFacts).length > 0 ? sampleFacts : undefined,
    };
  };

  /* ---- Evaluate ---- */

  const handleEvaluate = async () => {
    setError("");
    setResults([]);
    setSingleResult(null);

    if (ruleSource === "manual") {
      if (!statement.trim()) {
        setError("Rule statement is required.");
        return;
      }
      setLoading(true);
      try {
        const res = await playgroundEvaluate({
          rule_statement: statement,
          rule_modality: modality,
          rule_severity: severity,
          ...buildInput(),
        });
        setSingleResult(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Evaluation failed");
      } finally {
        setLoading(false);
      }
    } else {
      if (selectedRules.length === 0) {
        setError("Select at least one rule to evaluate.");
        return;
      }
      setLoading(true);
      const input = buildInput();
      const allResults: Array<{ rule: SelectedRule; result: PlaygroundResult }> = [];

      for (const rule of selectedRules) {
        try {
          const res = await playgroundEvaluate({
            rule_statement: rule.statement,
            rule_modality: rule.modality,
            rule_severity: rule.severity,
            ...input,
          });
          allResults.push({ rule, result: res });
          // Update results incrementally
          setResults([...allResults]);
        } catch (err) {
          allResults.push({
            rule,
            result: {
              verdict: "ERROR",
              confidence: 0,
              reasoning: err instanceof Error ? err.message : "Evaluation failed",
              issue_description: "",
              fix_suggestion: null,
              locations: [],
            },
          });
          setResults([...allResults]);
        }
      }
      setLoading(false);
    }
  };

  /* ---- Suggest input by LLM ---- */

  const handleSuggestInput = async (violating: boolean) => {
    setSuggesting(true);
    setSuggestDescription("");
    setError("");

    const payload: Record<string, unknown> = {
      input_mode: inputMode,
      violating,
    };

    if (ruleSource === "existing" && selectedRules.length > 0) {
      // Use the first selected rule for suggestion
      payload.rule_id = selectedRules[0].id;
    } else if (ruleSource === "manual" && statement.trim()) {
      payload.rule_statement = statement;
      payload.rule_modality = modality;
      payload.rule_severity = severity;
    } else {
      setError("Provide a rule first (select or type a statement).");
      setSuggesting(false);
      return;
    }

    try {
      const res: SuggestInputResult = await suggestInput(payload);
      if (res.sample_input) {
        if (inputMode === "code") {
          setSampleCode(res.sample_input);
        } else {
          setNarrative(res.sample_input);
        }
        setSuggestDescription(res.description);
      } else {
        setError(res.description || "No suggestion generated.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suggestion failed");
    } finally {
      setSuggesting(false);
    }
  };

  /* ---- Render helpers ---- */

  const renderResult = (result: PlaygroundResult, ruleLabel?: string) => (
    <div className="space-y-4 rounded-lg border bg-white p-6">
      {ruleLabel && (
        <p className="text-sm font-medium text-gray-700">{ruleLabel}</p>
      )}
      <div className="flex items-center gap-4">
        <VerdictBadge verdict={result.verdict} />
        <span className="text-sm text-gray-600">
          Confidence:{" "}
          <span className="font-semibold">
            {(result.confidence * 100).toFixed(0)}%
          </span>
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
          <h3 className="mb-1 text-sm font-semibold text-blue-800">
            Fix Suggestion
          </h3>
          <p className="text-sm text-blue-700">{result.fix_suggestion}</p>
        </div>
      )}

      {result.locations.length > 0 && (
        <div>
          <h3 className="mb-1 text-sm font-semibold text-gray-700">
            Locations
          </h3>
          <ul className="space-y-1">
            {result.locations.map((loc: { file_path: string; start_line: number | null; function_name: string | null }, i: number) => (
              <li key={i} className="text-sm text-gray-600">
                <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">
                  {loc.file_path}
                  {loc.start_line != null && `:${loc.start_line}`}
                </code>
                {loc.function_name && (
                  <span className="ml-2 text-gray-400">
                    ({loc.function_name})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  /* ---- Render ---- */

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold" title="Sandbox for testing rules against code or scenarios before deployment">Rule Playground</h1>
        <p className="mt-1 text-sm text-gray-500">
          Test rules against code changes or real-world scenarios before
          deploying
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
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500" title="Select existing rules or manually define a rule to test">
              Rule Definition
            </h2>
            <div className="flex gap-2">
              <TabButton
                active={ruleSource === "existing"}
                label="Pick Rules"
                onClick={() => setRuleSource("existing")}
              />
              <TabButton
                active={ruleSource === "manual"}
                label="Manual"
                onClick={() => setRuleSource("manual")}
              />
            </div>
          </div>

          {ruleSource === "existing" && (
            <RuleSearchPicker
              selectedRules={selectedRules}
              onAdd={addRule}
              onRemove={removeRule}
            />
          )}

          {ruleSource === "manual" && (
            <>
              <div>
                <label
                  htmlFor="statement"
                  className="mb-1 block text-sm font-medium text-gray-700"
                >
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
                  <label
                    htmlFor="modality"
                    className="mb-1 block text-sm font-medium text-gray-700"
                  >
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
                  <label
                    htmlFor="severity"
                    className="mb-1 block text-sm font-medium text-gray-700"
                  >
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
            </>
          )}
        </div>

        {/* ============ Right panel: Input ============ */}
        <div className="space-y-4 rounded-lg border bg-white p-5">
          {/* Mode tabs + Suggest button */}
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500" title="Provide code or a scenario description to evaluate against the rule">
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
              <div>
                <label className="mb-1 block text-xs text-gray-500">
                  Describe the situation
                </label>
                <textarea
                  rows={5}
                  className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="e.g. Employee John (ID: E001) submitted 52 hours of overtime for April 2026."
                  value={narrative}
                  onChange={(e) => setNarrative(e.target.value)}
                />
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label className="text-xs text-gray-500">
                    Structured facts{" "}
                    <span className="text-gray-400">(optional)</span>
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
                    No structured facts added. Click &quot;+ Add fact&quot; to
                    add key-value pairs like{" "}
                    <span className="font-mono">overtime_hours: 52</span>.
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
                          onChange={(e) =>
                            updateFact(i, "value", e.target.value)
                          }
                        />
                        <button
                          onClick={() => removeFact(i)}
                          className="flex-shrink-0 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
                          title="Remove fact"
                        >
                          <svg
                            className="h-4 w-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Suggest by LLM */}
          <div className="flex items-center gap-2 border-t pt-3">
            <span className="text-xs text-gray-400">Suggest by LLM:</span>
            <button
              onClick={() => handleSuggestInput(true)}
              disabled={suggesting}
              className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50"
            >
              {suggesting ? "Generating..." : "Violating Input"}
            </button>
            <button
              onClick={() => handleSuggestInput(false)}
              disabled={suggesting}
              className="rounded-md border border-green-200 bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100 disabled:opacity-50"
            >
              {suggesting ? "Generating..." : "Compliant Input"}
            </button>
          </div>
          {suggestDescription && (
            <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
              {suggestDescription}
            </p>
          )}
        </div>
      </div>

      {/* ============ Evaluate button ============ */}
      <div className="flex items-center justify-center gap-4">
        <button
          onClick={handleEvaluate}
          disabled={loading}
          title="Run the selected rule(s) against the provided input and see the verdict"
          className="rounded-md bg-blue-600 px-8 py-2.5 text-sm font-semibold text-white shadow hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading
            ? `Evaluating${ruleSource === "existing" && selectedRules.length > 1 ? ` (${results.length}/${selectedRules.length})` : ""}...`
            : ruleSource === "existing" && selectedRules.length > 1
              ? `Evaluate ${selectedRules.length} Rules`
              : "Evaluate"}
        </button>
      </div>

      {/* ============ Results ============ */}

      {/* Single rule result (manual mode) */}
      {singleResult && renderResult(singleResult)}

      {/* Multi-rule results (existing rules mode) */}
      {results.length > 0 && (
        <div className="space-y-4">
          {/* Summary bar */}
          <div className="flex items-center gap-4 rounded-lg border bg-white px-5 py-3">
            <span className="text-sm font-medium text-gray-700">
              Results: {results.length}/{selectedRules.length} rules
            </span>
            <div className="flex gap-3 text-sm">
              <span className="text-green-600">
                {results.filter((r) => r.result.verdict === "ALLOW").length} ALLOW
              </span>
              <span className="text-red-600">
                {results.filter((r) => r.result.verdict === "DENY").length} DENY
              </span>
              {results.filter((r) => r.result.verdict === "NEEDS_CONFIRMATION").length > 0 && (
                <span className="text-yellow-600">
                  {results.filter((r) => r.result.verdict === "NEEDS_CONFIRMATION").length} NEEDS_CONFIRMATION
                </span>
              )}
              {results.filter((r) => r.result.verdict === "ERROR").length > 0 && (
                <span className="text-gray-500">
                  {results.filter((r) => r.result.verdict === "ERROR").length} ERROR
                </span>
              )}
            </div>
          </div>

          {/* Per-rule results */}
          {results.map(({ rule, result }, i) =>
            <div key={`${rule.id}-${i}`}>
              {renderResult(
                result,
                `${rule.modality} | ${rule.statement.length > 100 ? rule.statement.slice(0, 100) + "..." : rule.statement}`,
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
