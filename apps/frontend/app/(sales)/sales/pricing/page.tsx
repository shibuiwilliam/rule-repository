"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface PricingApproval {
  id: string;
  deal: string;
  rep: string;
  listPrice: number;
  requestedPrice: number;
  discountPct: number;
  approver: string;
  status: string;
}

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  escalated: "bg-red-100 text-red-700",
  approved: "bg-green-100 text-green-700",
};

function formatJPY(n: number) {
  return `¥${n.toLocaleString()}`;
}

export default function PricingApprovalsPage() {
  const [approvals, setApprovals] = useState<PricingApproval[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ pricing_approvals: PricingApproval[] }>("sales").then((d) => {
      setApprovals(d.pricing_approvals ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Pricing Approvals</h1>
        <p className="mt-1 text-sm text-gray-500">Review and approve pricing exceptions against sales rules</p>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="divide-y">
          {approvals.map((a) => (
            <div key={a.id} className="flex items-start gap-4 px-5 py-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">{a.deal}</p>
                <p className="mt-0.5 text-xs text-gray-500">Rep: {a.rep} · Approver: {a.approver}</p>
                <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                  <span>List: {formatJPY(a.listPrice)}</span>
                  <span>→</span>
                  <span className="font-medium text-gray-900">{formatJPY(a.requestedPrice)}</span>
                  <span className="rounded bg-orange-100 px-1.5 py-0.5 font-medium text-orange-700">-{a.discountPct}%</span>
                </div>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[a.status]}`}>{a.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
