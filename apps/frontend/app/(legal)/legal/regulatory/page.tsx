"use client";

import { useState, useEffect } from "react";
import { usePersonaTerm } from "@/lib/use-persona-term";
import { fetchSeedData } from "@/lib/seed-data";

interface RegulatoryItem {
  id: string;
  title: string;
  authority: string;
  effective_date: string;
  impact: "high" | "medium" | "low";
  status: "upcoming" | "effective" | "proposed";
  affected_rules: number;
}


const IMPACT_BADGE: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-gray-100 text-gray-600",
};

const STATUS_BADGE: Record<string, string> = {
  upcoming: "bg-blue-100 text-blue-700",
  effective: "bg-green-100 text-green-700",
  proposed: "bg-gray-100 text-gray-600",
};

export default function RegulatoryHorizonPage() {
  const t = usePersonaTerm();
  const [items, setItems] = useState<RegulatoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ regulatory: RegulatoryItem[] }>("legal").then((d) => {
      setItems(d.regulatory ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("regulatory_title", "Regulatory Horizon")}</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upcoming regulatory changes and their impact on internal rules
        </p>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="divide-y">
          {items.map((item) => (
            <div key={item.id} className="flex items-start gap-4 px-5 py-4">
              <div className="w-24 shrink-0 pt-0.5">
                <p className="text-sm font-semibold text-gray-900">
                  {item.effective_date.split("-").slice(1).join("/")}
                </p>
                <p className="text-xs text-gray-400">
                  {item.effective_date.split("-")[0]}
                </p>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">{item.title}</p>
                <p className="mt-0.5 text-xs text-gray-500">{item.authority}</p>
                <p className="mt-1 text-xs text-gray-400">
                  {item.affected_rules} rule{item.affected_rules !== 1 ? "s" : ""} affected
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[item.status]}`}>
                  {item.status}
                </span>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${IMPACT_BADGE[item.impact]}`}>
                  {item.impact}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
