"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface BrandRule {
  id: number;
  category: string;
  title: string;
  description: string;
  modality: "MUST" | "MUST_NOT" | "SHOULD";
  examples: string[];
}

const MODALITY_STYLES: Record<string, string> = {
  MUST: "bg-blue-100 text-blue-800",
  MUST_NOT: "bg-red-100 text-red-800",
  SHOULD: "bg-yellow-100 text-yellow-800",
};

export default function BrandRulesPage() {
  const [brandRules, setBrandRules] = useState<BrandRule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ brand_rules: BrandRule[] }>("marketing").then((d) => {
      setBrandRules(d.brand_rules ?? []);
      setLoading(false);
    });
  }, []);

  const categories = [...new Set(brandRules.map((r) => r.category))];

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Brand Rules</h1>
        <p className="mt-1 text-sm text-gray-500">
          Brand guideline rules governing logo usage, color palette, typography, and tone of
          voice across all marketing materials
        </p>
      </div>

      {categories.map((category) => (
        <div key={category} className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-800">{category}</h2>
          {brandRules.filter((r) => r.category === category).map((rule) => (
            <div key={rule.id} className="rounded-xl border bg-white p-5">
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-sm font-semibold text-gray-900">{rule.title}</h3>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${MODALITY_STYLES[rule.modality]}`}
                >
                  {rule.modality}
                </span>
              </div>
              <p className="mt-1 text-sm text-gray-600">{rule.description}</p>
              <div className="mt-3 space-y-1">
                {rule.examples.map((ex, i) => (
                  <p key={i} className="text-xs text-gray-500">
                    {ex}
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
