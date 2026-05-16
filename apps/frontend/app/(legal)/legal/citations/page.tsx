"use client";

import { useState, useEffect } from "react";
import { usePersonaTerm } from "@/lib/use-persona-term";
import { fetchSeedData } from "@/lib/seed-data";

interface Citation {
  rule_id: string;
  rule_statement: string;
  source_title: string;
  source_section: string;
  norm_tier: string;
  jurisdiction: string;
}


const TIER_BADGE: Record<string, string> = {
  LAW: "bg-red-100 text-red-700",
  REGULATION: "bg-orange-100 text-orange-700",
  CORPORATE_POLICY: "bg-blue-100 text-blue-700",
  DEPARTMENT_RULE: "bg-gray-100 text-gray-600",
};

export default function CitationsPage() {
  const t = usePersonaTerm();
  const [citations, setCitations] = useState<Citation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ citations: Citation[] }>("legal").then((d) => {
      setCitations(d.citations ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("citations_title", "Rule Citations")}</h1>
        <p className="mt-1 text-sm text-gray-500">
          Source references and provenance for legal rules
        </p>
      </div>

      <div className="rounded-xl border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-gray-50">
            <tr>
              <th className="px-5 py-3 font-medium text-gray-600">Rule</th>
              <th className="px-5 py-3 font-medium text-gray-600">Source</th>
              <th className="px-5 py-3 font-medium text-gray-600">Tier</th>
              <th className="px-5 py-3 font-medium text-gray-600">Jurisdiction</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {citations.map((c) => (
              <tr key={c.rule_id}>
                <td className="px-5 py-3">
                  <p className="font-medium text-gray-900">{c.rule_statement}</p>
                  <p className="text-xs text-gray-400">{c.rule_id}</p>
                </td>
                <td className="px-5 py-3">
                  <p className="text-gray-700">{c.source_title}</p>
                  <p className="text-xs text-gray-400">{c.source_section}</p>
                </td>
                <td className="px-5 py-3">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${TIER_BADGE[c.norm_tier] ?? "bg-gray-100 text-gray-600"}`}>
                    {c.norm_tier.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-5 py-3 text-gray-600">{c.jurisdiction}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
