"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

interface ClauseVerdict {
  clause_id: string;
  clause_type: string;
  verdict: string;
  confidence: number;
  reasoning: string;
  issue_description: string;
  revised_text: string;
  risk_level: string;
}

interface ContractReview {
  evaluation_id: string;
  contract_verdict: string;
  clause_verdicts: ClauseVerdict[];
  critical_clause_ids: string[];
  warning_clause_ids: string[];
  clause_risk_scores: Record<string, number>;
  rules_evaluated: number;
  rules_violated: number;
}

const VERDICT_COLORS: Record<string, string> = {
  ALLOW: "bg-green-100 text-green-800 border-green-300",
  DENY: "bg-red-100 text-red-800 border-red-300",
  NEEDS_CONFIRMATION: "bg-yellow-100 text-yellow-800 border-yellow-300",
};

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-50 border-l-green-500",
  medium: "bg-yellow-50 border-l-yellow-500",
  high: "bg-red-50 border-l-red-500",
};

export default function ContractReviewPage() {
  const params = useParams();
  const contractId = params.id as string;
  const [review, _setReview] = useState<ContractReview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In production, fetch from POST /api/v1/evaluate/contract
    // For now, show a placeholder
    setLoading(false);
  }, [contractId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-700" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Contract Review</h1>
        <p className="text-gray-500 mt-1">Contract ID: {contractId}</p>
      </div>

      {review ? (
        <div className="grid grid-cols-3 gap-6">
          {/* Left panel: Contract clauses */}
          <div className="col-span-2 space-y-4">
            <h2 className="text-lg font-semibold">Clauses</h2>
            {review.clause_verdicts.map((cv) => (
              <div
                key={cv.clause_id}
                className={`border-l-4 p-4 rounded-r ${RISK_COLORS[cv.risk_level] || "bg-gray-50"}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{cv.clause_id}</span>
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium border ${VERDICT_COLORS[cv.verdict] || "bg-gray-100"}`}
                  >
                    {cv.verdict}
                  </span>
                </div>
                <p className="text-sm text-gray-700">{cv.reasoning}</p>
                {cv.issue_description && (
                  <p className="text-sm text-red-700 mt-2">{cv.issue_description}</p>
                )}
                {cv.revised_text && (
                  <div className="mt-3 p-3 bg-white rounded border border-dashed border-blue-300">
                    <p className="text-xs font-medium text-blue-700 mb-1">Suggested revision:</p>
                    <p className="text-sm">{cv.revised_text}</p>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Right panel: Summary */}
          <div className="space-y-4">
            <div className="bg-white p-4 rounded-lg border">
              <h3 className="font-medium mb-3">Summary</h3>
              <div
                className={`text-center p-3 rounded mb-4 ${VERDICT_COLORS[review.contract_verdict] || "bg-gray-100"}`}
              >
                <span className="text-lg font-bold">{review.contract_verdict}</span>
              </div>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Rules evaluated</dt>
                  <dd className="font-medium">{review.rules_evaluated}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Violations</dt>
                  <dd className="font-medium text-red-600">{review.rules_violated}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Critical clauses</dt>
                  <dd className="font-medium text-red-600">{review.critical_clause_ids.length}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white p-8 rounded-lg border text-center">
          <p className="text-gray-500">
            Upload a contract or paste contract text to begin review.
          </p>
          <p className="text-sm text-gray-400 mt-2">
            Uses POST /api/v1/evaluate/contract with the Contract Clause Engine.
          </p>
        </div>
      )}
    </div>
  );
}
