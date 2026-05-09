"use client";

interface RegulatoryUpdate {
  id: string;
  title: string;
  source: string;
  normTier: string;
  publishedAt: string;
  effectiveAt: string;
  impactedRules: number;
  status: "new" | "assessed" | "propagated" | "resolved";
  summary: string;
}

const UPDATES: RegulatoryUpdate[] = [
  { id: "REG-001", title: "Amendment to Labor Standards Act Article 36 (overtime caps)", source: "Ministry of Health, Labour and Welfare", normTier: "LAW", publishedAt: "2026-04-15", effectiveAt: "2026-10-01", impactedRules: 8, status: "assessed", summary: "Monthly overtime cap revised from 45 to 40 hours for companies with 50+ employees. Special clause thresholds unchanged." },
  { id: "REG-002", title: "APPI Enforcement Regulation Amendment", source: "Personal Information Protection Commission", normTier: "REGULATION", publishedAt: "2026-04-20", effectiveAt: "2026-07-01", impactedRules: 5, status: "new", summary: "New breach notification requirements: 72-hour reporting window, expanded scope of reportable incidents." },
  { id: "REG-003", title: "Revised Invoice System Qualification Requirements", source: "National Tax Agency", normTier: "REGULATION", publishedAt: "2026-03-01", effectiveAt: "2026-04-01", impactedRules: 3, status: "propagated", summary: "Qualified invoice issuer registration requirements updated. Small business transitional period extended." },
  { id: "REG-004", title: "Child Care and Family Care Leave Act Amendment", source: "Ministry of Health, Labour and Welfare", normTier: "LAW", publishedAt: "2026-05-01", effectiveAt: "2027-04-01", impactedRules: 6, status: "new", summary: "Extended childcare leave eligibility to include part-time workers. New employer disclosure requirements." },
];

const TIER_BADGE: Record<string, string> = { LAW: "bg-red-100 text-red-800", REGULATION: "bg-orange-100 text-orange-800", GUIDELINE: "bg-yellow-100 text-yellow-800" };
const STATUS_BADGE: Record<string, string> = { new: "bg-blue-100 text-blue-800", assessed: "bg-yellow-100 text-yellow-800", propagated: "bg-green-100 text-green-800", resolved: "bg-gray-100 text-gray-700" };

export default function RegulatoryFeedPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Regulatory Feed</h1>
        <p className="mt-1 text-sm text-gray-500">Track upstream regulatory changes and their downstream impact on internal rules</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "New Updates", value: UPDATES.filter((u) => u.status === "new").length, color: "text-blue-600" },
          { label: "Being Assessed", value: UPDATES.filter((u) => u.status === "assessed").length, color: "text-yellow-600" },
          { label: "Propagated", value: UPDATES.filter((u) => u.status === "propagated").length, color: "text-green-600" },
          { label: "Total Impacted Rules", value: UPDATES.reduce((a, u) => a + u.impactedRules, 0), color: "text-red-600" },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>
      <div className="space-y-3">
        {UPDATES.map((u) => (
          <div key={u.id} className="rounded-xl border bg-white p-5 hover:border-amber-300 transition-colors">
            <div className="flex items-center gap-2">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${TIER_BADGE[u.normTier] ?? "bg-gray-100 text-gray-700"}`}>{u.normTier}</span>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[u.status]}`}>{u.status}</span>
              <span className="text-xs text-gray-400">{u.id}</span>
            </div>
            <h3 className="mt-2 text-sm font-semibold text-gray-900">{u.title}</h3>
            <p className="mt-1 text-sm text-gray-600">{u.summary}</p>
            <div className="mt-2 flex gap-4 text-xs text-gray-400">
              <span>Source: {u.source}</span>
              <span>Published: {u.publishedAt}</span>
              <span>Effective: {u.effectiveAt}</span>
              <span className="text-red-500">{u.impactedRules} rule(s) impacted</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
