"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface Campaign {
  id: string;
  name: string;
  channel: string;
  launchDate: string;
  status: "approved" | "pending_review" | "violations_found" | "draft";
  rulesChecked: number;
  violations: number;
}

const STATUS_STYLES: Record<string, { bg: string; label: string }> = {
  approved: { bg: "bg-green-100 text-green-800", label: "Approved" },
  pending_review: { bg: "bg-yellow-100 text-yellow-800", label: "Pending Review" },
  violations_found: { bg: "bg-red-100 text-red-800", label: "Violations Found" },
  draft: { bg: "bg-gray-100 text-gray-600", label: "Draft" },
};

export default function CampaignAuditPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ campaigns: Campaign[] }>("marketing").then((d) => {
      setCampaigns(d.campaigns ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Campaign Audit</h1>
        <p className="mt-1 text-sm text-gray-500">
          Review campaign compliance status across all channels. Each campaign is checked
          against applicable advertising regulations, brand guidelines, and internal policies.
        </p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-xl border bg-white p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{campaigns.length}</p>
          <p className="text-xs text-gray-500">Total Campaigns</p>
        </div>
        <div className="rounded-xl border bg-white p-4 text-center">
          <p className="text-2xl font-bold text-green-600">
            {campaigns.filter((c) => c.status === "approved").length}
          </p>
          <p className="text-xs text-gray-500">Approved</p>
        </div>
        <div className="rounded-xl border bg-white p-4 text-center">
          <p className="text-2xl font-bold text-yellow-600">
            {campaigns.filter((c) => c.status === "pending_review").length}
          </p>
          <p className="text-xs text-gray-500">Pending Review</p>
        </div>
        <div className="rounded-xl border bg-white p-4 text-center">
          <p className="text-2xl font-bold text-red-600">
            {campaigns.filter((c) => c.status === "violations_found").length}
          </p>
          <p className="text-xs text-gray-500">Violations Found</p>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Campaign</th>
              <th className="px-4 py-3">Channel</th>
              <th className="px-4 py-3">Launch Date</th>
              <th className="px-4 py-3">Rules Checked</th>
              <th className="px-4 py-3">Violations</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {campaigns.map((campaign) => {
              const style = STATUS_STYLES[campaign.status];
              return (
                <tr key={campaign.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{campaign.name}</p>
                    <p className="text-xs text-gray-400">{campaign.id}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{campaign.channel}</td>
                  <td className="px-4 py-3 text-gray-500">{campaign.launchDate}</td>
                  <td className="px-4 py-3 text-gray-600">{campaign.rulesChecked}</td>
                  <td className="px-4 py-3">
                    {campaign.violations > 0 ? (
                      <span className="font-medium text-red-600">{campaign.violations}</span>
                    ) : (
                      <span className="text-gray-400">0</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${style?.bg ?? "bg-gray-100 text-gray-700"}`}
                    >
                      {style?.label ?? campaign.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
