"use client";

import { usePersonaTerm } from "@/lib/use-persona-term";

interface Citation {
  rule_id: string;
  rule_statement: string;
  source_title: string;
  source_section: string;
  norm_tier: string;
  jurisdiction: string;
}

const SAMPLE_CITATIONS: Citation[] = [
  { rule_id: "R-L001", rule_statement: "NDA must include a 2-year minimum confidentiality period", source_title: "Corporate NDA Template v3", source_section: "Section 5.1", norm_tier: "CORPORATE_POLICY", jurisdiction: "Global" },
  { rule_id: "R-L002", rule_statement: "Anti-social forces exclusion clause is mandatory", source_title: "Civil Code (JP)", source_section: "Article 90", norm_tier: "LAW", jurisdiction: "JP" },
  { rule_id: "R-L003", rule_statement: "Limitation of liability must not exceed contract value", source_title: "Standard MSA Template", source_section: "Section 8.2", norm_tier: "CORPORATE_POLICY", jurisdiction: "Global" },
  { rule_id: "R-L004", rule_statement: "Personal data handling must comply with APPI", source_title: "Act on Protection of Personal Information", source_section: "Chapter 4", norm_tier: "LAW", jurisdiction: "JP" },
  { rule_id: "R-L005", rule_statement: "Governing law must be specified in all contracts", source_title: "Legal Department Guidelines", source_section: "Section 2.3", norm_tier: "DEPARTMENT_RULE", jurisdiction: "Global" },
];

const TIER_BADGE: Record<string, string> = {
  LAW: "bg-red-100 text-red-700",
  REGULATION: "bg-orange-100 text-orange-700",
  CORPORATE_POLICY: "bg-blue-100 text-blue-700",
  DEPARTMENT_RULE: "bg-gray-100 text-gray-600",
};

export default function CitationsPage() {
  const t = usePersonaTerm();

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
            {SAMPLE_CITATIONS.map((c) => (
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
