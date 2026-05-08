"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

interface RuleVerdict {
  rule_id: string;
  rule_statement: string;
  verdict: string;
  confidence: number;
  reasoning: string;
  issue_description: string;
}

interface EventReview {
  evaluation_id: string;
  overall_verdict: string;
  rule_verdicts: RuleVerdict[];
  rules_evaluated: number;
  rules_violated: number;
  rules_uncertain: number;
}

const VERDICT_BADGES: Record<string, string> = {
  ALLOW: "bg-green-100 text-green-800",
  DENY: "bg-red-100 text-red-800",
  NEEDS_CONFIRMATION: "bg-yellow-100 text-yellow-800",
};

export default function EventReviewPage() {
  const params = useParams();
  const eventId = params.id as string;
  const [review, _setReview] = useState<EventReview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In production, fetch from POST /api/v1/evaluate/event
    setLoading(false);
  }, [eventId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-700" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Event Compliance Review</h1>
        <p className="text-gray-500 mt-1">Event ID: {eventId}</p>
      </div>

      {review ? (
        <div className="space-y-6">
          {/* Overall verdict */}
          <div className="bg-white p-6 rounded-lg border">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Overall Verdict</h2>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${VERDICT_BADGES[review.overall_verdict] || "bg-gray-100"}`}>
                {review.overall_verdict}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="text-center">
                <p className="text-2xl font-bold">{review.rules_evaluated}</p>
                <p className="text-sm text-gray-500">Rules checked</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-red-600">{review.rules_violated}</p>
                <p className="text-sm text-gray-500">Violations</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-600">{review.rules_uncertain}</p>
                <p className="text-sm text-gray-500">Needs review</p>
              </div>
            </div>
          </div>

          {/* Per-rule verdicts */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold">Rule Results</h2>
            {review.rule_verdicts.map((rv) => (
              <div key={rv.rule_id} className="bg-white p-4 rounded-lg border">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{rv.rule_statement}</p>
                    <p className="text-sm text-gray-600 mt-1">{rv.reasoning}</p>
                    {rv.issue_description && (
                      <p className="text-sm text-red-600 mt-1">{rv.issue_description}</p>
                    )}
                  </div>
                  <span className={`ml-4 px-2 py-1 rounded text-xs font-medium ${VERDICT_BADGES[rv.verdict] || "bg-gray-100"}`}>
                    {rv.verdict}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-white p-8 rounded-lg border text-center">
          <p className="text-gray-500">
            Submit an event to evaluate against HR rules.
          </p>
          <p className="text-sm text-gray-400 mt-2">
            Supports single, sequence (monthly), and calendar (annual) evaluation modes.
          </p>
        </div>
      )}
    </div>
  );
}
