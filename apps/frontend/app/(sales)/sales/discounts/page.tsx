"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface DiscountRule {
  tier: string;
  authority: string;
  approval: string;
  conditions: string;
}

export default function DiscountRequestsPage() {
  const [discountRules, setDiscountRules] = useState<DiscountRule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ discount_rules: DiscountRule[] }>("sales").then((d) => {
      setDiscountRules(d.discount_rules ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Discount Requests</h1>
        <p className="mt-1 text-sm text-gray-500">Discount authority matrix and recent requests</p>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Discount Authority Matrix</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="px-4 py-2 font-medium text-gray-600">Discount Tier</th>
                <th className="px-4 py-2 font-medium text-gray-600">Authority</th>
                <th className="px-4 py-2 font-medium text-gray-600">Approval</th>
                <th className="px-4 py-2 font-medium text-gray-600">Conditions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {discountRules.map((r) => (
                <tr key={r.tier}>
                  <td className="px-4 py-2 font-medium text-gray-900">{r.tier}</td>
                  <td className="px-4 py-2">{r.authority}</td>
                  <td className="px-4 py-2">{r.approval}</td>
                  <td className="px-4 py-2 text-gray-500">{r.conditions}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
