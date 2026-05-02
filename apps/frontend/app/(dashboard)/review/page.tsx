"use client";

import { useState } from "react";
import Link from "next/link";
import Badge from "@/components/Badge";
import {
  type RoughReviewResponse,
  type DetailedReviewResponse,
  type CombinedReviewResponse,
  type RuleRelevanceItem,
  roughReview,
  combinedReview,
} from "@/lib/api";
import { useProject } from "@/lib/project-context";

type InputMode = "code" | "scenario";

const RELEVANCE_COLORS: Record<string, string> = {
  RELEVANT: "bg-green-100 text-green-800",
  POTENTIALLY_RELEVANT: "bg-yellow-100 text-yellow-800",
  NOT_RELEVANT: "bg-gray-100 text-gray-500",
};

const VERDICT_COLORS: Record<string, string> = {
  ALLOW: "bg-green-100 text-green-800 border-green-300",
  DENY: "bg-red-100 text-red-800 border-red-300",
  NEEDS_CONFIRMATION: "bg-yellow-100 text-yellow-800 border-yellow-300",
};

export default function ReviewPage() {
  const { currentProject } = useProject();
  const [inputMode, setInputMode] = useState<InputMode>("code");
  const [sampleCode, setSampleCode] = useState("");
  const [narrative, setNarrative] = useState("");
  const [intent, setIntent] = useState("");

  const [roughResult, setRoughResult] = useState<RoughReviewResponse | null>(null);
  const [detailedResult, setDetailedResult] = useState<DetailedReviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"idle" | "rough" | "full">("idle");

  const buildPayload = () => {
    const payload: Record<string, unknown> = {};
    if (inputMode === "code" && sampleCode.trim()) {
      payload.diff = sampleCode;
    } else if (inputMode === "scenario" && narrative.trim()) {
      payload.facts = { narrative: narrative.trim() };
    }
    if (intent.trim()) payload.intent = intent.trim();
    if (currentProject?.id) payload.project_id = currentProject.id;
    return payload;
  };

  const handleRoughReview = async () => {
    setLoading(true);
    setError("");
    setRoughResult(null);
    setDetailedResult(null);
    setMode("rough");
    try {
      const result = await roughReview(buildPayload());
      setRoughResult(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setLoading(false);
    }
  };

  const handleFullReview = async () => {
    setLoading(true);
    setError("");
    setRoughResult(null);
    setDetailedResult(null);
    setMode("full");
    try {
      const result: CombinedReviewResponse = await combinedReview(buildPayload());
      setRoughResult(result.rough_review);
      setDetailedResult(result.detailed_review);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Activity Review</h1>
        <p className="mt-1 text-sm text-gray-500">
          Review an activity against ALL registered rules with two-tier compliance checking
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Input Section */}
      <div className="rounded-lg border bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Activity Description
          </h2>
          <div className="flex gap-2">
            <button
              onClick={() => setInputMode("code")}
              className={`rounded-md px-4 py-1.5 text-sm font-medium ${
                inputMode === "code" ? "bg-blue-600 text-white" : "border border-gray-300 text-gray-600"
              }`}
            >
              Code
            </button>
            <button
              onClick={() => setInputMode("scenario")}
              className={`rounded-md px-4 py-1.5 text-sm font-medium ${
                inputMode === "scenario" ? "bg-blue-600 text-white" : "border border-gray-300 text-gray-600"
              }`}
            >
              Scenario
            </button>
          </div>
        </div>

        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">Intent</label>
          <input
            type="text"
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="What is this activity about?"
            className="w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        {inputMode === "code" ? (
          <textarea
            rows={10}
            value={sampleCode}
            onChange={(e) => setSampleCode(e.target.value)}
            placeholder="Paste code diff or snippet..."
            className="w-full rounded-md border px-3 py-2 font-mono text-sm"
          />
        ) : (
          <textarea
            rows={6}
            value={narrative}
            onChange={(e) => setNarrative(e.target.value)}
            placeholder="Describe the activity, decision, or situation..."
            className="w-full rounded-md border px-3 py-2 text-sm"
          />
        )}

        <div className="mt-4 flex gap-3">
          <button
            onClick={handleRoughReview}
            disabled={loading}
            className="rounded-md border border-blue-600 px-6 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 disabled:opacity-50"
          >
            {loading && mode === "rough" ? "Scanning..." : "Rough Review (fast)"}
          </button>
          <button
            onClick={handleFullReview}
            disabled={loading}
            className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading && mode === "full" ? "Reviewing..." : "Full Review (rough + detailed)"}
          </button>
        </div>
      </div>

      {/* Rough Review Results */}
      {roughResult && (
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border bg-white px-5 py-3">
            <div>
              <h3 className="text-sm font-semibold">Tier 1: Rough Compliance Scan</h3>
              <p className="text-xs text-gray-500">
                {roughResult.total_rules_scanned} rules scanned in {roughResult.latency_ms}ms
                {roughResult.llm_triage_used && " (LLM triage applied)"}
              </p>
            </div>
            <div className="flex gap-3 text-sm">
              <span className="text-green-600">{roughResult.relevant_count} relevant</span>
              <span className="text-yellow-600">{roughResult.potentially_relevant_count} potential</span>
              <span className="text-gray-400">{roughResult.not_relevant_count} not relevant</span>
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border bg-white">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Rule</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Modality</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Severity</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Relevance</th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {roughResult.rule_assessments
                  .filter((a: RuleRelevanceItem) => a.relevance !== "NOT_RELEVANT")
                  .map((a: RuleRelevanceItem) => (
                    <tr key={a.rule_id} className="hover:bg-gray-50">
                      <td className="max-w-md px-4 py-2">
                        <Link href={`/rules/${a.rule_id}`} className="text-sm text-blue-600 hover:underline">
                          {a.rule_statement.length > 100 ? `${a.rule_statement.slice(0, 100)}...` : a.rule_statement}
                        </Link>
                      </td>
                      <td className="px-4 py-2"><Badge label={a.modality} variant="modality" /></td>
                      <td className="px-4 py-2"><Badge label={a.severity} variant="severity" /></td>
                      <td className="px-4 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${RELEVANCE_COLORS[a.relevance] ?? "bg-gray-100"}`}>
                          {a.relevance.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-right text-sm text-gray-500">{a.relevance_score.toFixed(2)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detailed Review Results */}
      {detailedResult && detailedResult.rules_evaluated > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border bg-white px-5 py-3">
            <div>
              <h3 className="text-sm font-semibold">Tier 2: Detailed Compliance Evaluation</h3>
              <p className="text-xs text-gray-500">
                {detailedResult.rules_evaluated} rules evaluated in {detailedResult.chunk_count} batch{detailedResult.chunk_count !== 1 ? "es" : ""} ({detailedResult.total_latency_ms}ms)
              </p>
            </div>
            <span className={`rounded-full border px-4 py-1.5 text-sm font-semibold ${VERDICT_COLORS[detailedResult.overall_verdict] ?? "bg-gray-100"}`}>
              {detailedResult.overall_verdict}
            </span>
          </div>

          <div className="flex gap-4 text-sm">
            <span className="text-green-600">{detailedResult.rules_passed} passed</span>
            <span className="text-red-600">{detailedResult.rules_violated} violated</span>
            <span className="text-yellow-600">{detailedResult.rules_uncertain} uncertain</span>
          </div>

          {detailedResult.fix_summary && (
            <div className="rounded-md border border-blue-200 bg-blue-50 p-4">
              <h4 className="mb-1 text-sm font-semibold text-blue-800">Fix Summary</h4>
              <p className="whitespace-pre-wrap text-sm text-blue-700">{detailedResult.fix_summary}</p>
            </div>
          )}

          <div className="space-y-3">
            {detailedResult.rule_verdicts.map((v) => (
              <div key={v.rule_id} className="rounded-lg border bg-white p-4">
                <div className="flex items-center justify-between">
                  <Link href={`/rules/${v.rule_id}`} className="text-sm font-medium text-blue-600 hover:underline">
                    {v.rule_statement.length > 120 ? `${v.rule_statement.slice(0, 120)}...` : v.rule_statement}
                  </Link>
                  <span className={`rounded-full border px-3 py-0.5 text-xs font-semibold ${VERDICT_COLORS[v.verdict] ?? "bg-gray-100"}`}>
                    {v.verdict} ({(v.confidence * 100).toFixed(0)}%)
                  </span>
                </div>
                {v.reasoning && (
                  <p className="mt-2 whitespace-pre-wrap rounded bg-gray-50 p-2 text-xs text-gray-600">
                    {v.reasoning}
                  </p>
                )}
                {v.fix_suggestion && (
                  <p className="mt-2 rounded border border-blue-200 bg-blue-50 p-2 text-xs text-blue-700">
                    Fix: {v.fix_suggestion}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
