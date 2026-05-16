"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface CommunicationReview {
  id: string;
  subject: string;
  channel: string;
  verdict: string;
  issues: number;
  reviewed: string;
}

const VERDICT_BADGE: Record<string, string> = {
  ALLOW: "bg-green-100 text-green-700",
  ALLOW_WITH_CONDITIONS: "bg-yellow-100 text-yellow-700",
  DENY: "bg-red-100 text-red-700",
};

export default function SalesCommunicationPage() {
  const [reviews, setReviews] = useState<CommunicationReview[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ communication_reviews: CommunicationReview[] }>("sales").then((d) => {
      setReviews(d.communication_reviews ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sales Communication Review</h1>
        <p className="mt-1 text-sm text-gray-500">Review outbound sales communications for policy compliance</p>
      </div>

      <div className="rounded-xl border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-gray-50">
            <tr>
              <th className="px-5 py-3 font-medium text-gray-600">Subject</th>
              <th className="px-5 py-3 font-medium text-gray-600">Channel</th>
              <th className="px-5 py-3 font-medium text-gray-600">Issues</th>
              <th className="px-5 py-3 font-medium text-gray-600">Verdict</th>
              <th className="px-5 py-3 font-medium text-gray-600">Reviewed</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {reviews.map((r) => (
              <tr key={r.id}>
                <td className="px-5 py-3 font-medium text-gray-900">{r.subject}</td>
                <td className="px-5 py-3 text-gray-600">{r.channel}</td>
                <td className="px-5 py-3">{r.issues || "—"}</td>
                <td className="px-5 py-3">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${VERDICT_BADGE[r.verdict]}`}>
                    {r.verdict.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-5 py-3 text-gray-500">{r.reviewed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
