"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface Proposal {
  id: string;
  title: string;
  status: string;
  author: string;
  created: string;
}

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  under_review: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
};

export default function SalesProposalsPage() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ proposals: Proposal[] }>("sales").then((d) => {
      setProposals(d.proposals ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sales Rule Proposals</h1>
        <p className="mt-1 text-sm text-gray-500">Proposed changes to sales pricing and discount rules</p>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="divide-y">
          {proposals.map((p) => (
            <div key={p.id} className="flex items-center gap-4 px-5 py-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">{p.title}</p>
                <p className="mt-0.5 text-xs text-gray-500">{p.id} · by {p.author} · {p.created}</p>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[p.status]}`}>
                {p.status.replace(/_/g, " ")}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
