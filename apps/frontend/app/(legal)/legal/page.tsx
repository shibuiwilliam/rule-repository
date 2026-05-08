import Link from "next/link";

const PENDING_CONTRACTS = [
  { id: "C-2401", title: "Cloud Infrastructure SLA", counterparty: "AWS Japan", type: "MSA", submittedAt: "2026-05-07", priority: "high" as const },
  { id: "C-2402", title: "Recruiting Agency Agreement", counterparty: "Recruit Co.", type: "Service Agreement", submittedAt: "2026-05-06", priority: "medium" as const },
  { id: "C-2403", title: "Marketing Platform License", counterparty: "HubSpot", type: "SaaS License", submittedAt: "2026-05-05", priority: "low" as const },
  { id: "C-2404", title: "NDA - Partner Integration", counterparty: "TechCorp Inc.", type: "NDA", submittedAt: "2026-05-04", priority: "high" as const },
];

const REGULATORY_CHANGES = [
  { id: "REG-101", title: "Revised Act on Protection of Personal Information (APPI) Guidelines", source: "PPC Japan", effectiveDate: "2026-07-01", impact: "high" as const, status: "action-required" as const },
  { id: "REG-102", title: "EU AI Act - High-Risk System Requirements", source: "European Commission", effectiveDate: "2026-08-01", impact: "high" as const, status: "new" as const },
  { id: "REG-103", title: "Updated Subcontract Act enforcement standards", source: "JFTC", effectiveDate: "2026-06-15", impact: "medium" as const, status: "reviewed" as const },
];

const PRIORITY_BADGE: Record<string, string> = { high: "bg-red-100 text-red-700", medium: "bg-yellow-100 text-yellow-700", low: "bg-gray-100 text-gray-600" };
const IMPACT_BADGE: Record<string, string> = { high: "bg-red-100 text-red-700", medium: "bg-yellow-100 text-yellow-700", low: "bg-green-100 text-green-700" };
const STATUS_BADGE: Record<string, string> = { new: "bg-blue-100 text-blue-700", reviewed: "bg-gray-100 text-gray-600", "action-required": "bg-red-100 text-red-700" };

export default function LegalDashboardPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Legal Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Contract pipeline, regulatory changes, and clause compliance</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Pending Reviews</p>
          <p className="mt-1 text-3xl font-bold text-yellow-600">4</p>
          <p className="mt-1 text-xs text-gray-400">2 high priority</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Clause Deviations</p>
          <p className="mt-1 text-3xl font-bold text-red-600">7</p>
          <p className="mt-1 text-xs text-gray-400">From standard templates</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Regulatory Updates</p>
          <p className="mt-1 text-3xl font-bold text-blue-600">4</p>
          <p className="mt-1 text-xs text-gray-400">2 require action</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Active Legal Rules</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">28</p>
          <p className="mt-1 text-xs text-gray-400">3 under review</p>
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Pending Contract Reviews</h2>
          <Link href="/legal/contracts" className="text-sm text-blue-600 hover:underline">View all</Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Title</th>
                <th className="px-5 py-3">Counterparty</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">Submitted</th>
                <th className="px-5 py-3">Priority</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {PENDING_CONTRACTS.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs text-gray-500">{c.id}</td>
                  <td className="px-5 py-3 font-medium text-gray-900">{c.title}</td>
                  <td className="px-5 py-3 text-gray-600">{c.counterparty}</td>
                  <td className="px-5 py-3 text-gray-600">{c.type}</td>
                  <td className="px-5 py-3 text-gray-500">{c.submittedAt}</td>
                  <td className="px-5 py-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${PRIORITY_BADGE[c.priority]}`}>{c.priority}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Regulatory Changes Timeline</h2>
        </div>
        <div className="divide-y">
          {REGULATORY_CHANGES.map((r) => (
            <div key={r.id} className="flex items-start gap-4 px-5 py-4">
              <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-medium text-gray-600">
                {r.effectiveDate.split("-")[1]}/{r.effectiveDate.split("-")[2]}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">{r.title}</p>
                <p className="mt-0.5 text-xs text-gray-500">Source: {r.source} | Effective: {r.effectiveDate}</p>
              </div>
              <div className="flex gap-2">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${IMPACT_BADGE[r.impact]}`}>{r.impact} impact</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[r.status]}`}>{r.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Clause Deviation Alerts</h2>
        <div className="mt-4 space-y-3">
          {[
            { clause: "Limitation of Liability", contract: "C-2401 (AWS Japan)", severity: "high", detail: "Cap exceeds 2x annual fees standard" },
            { clause: "Indemnification", contract: "C-2404 (TechCorp Inc.)", severity: "high", detail: "Mutual indemnification missing from NDA" },
            { clause: "Data Processing", contract: "C-2403 (HubSpot)", severity: "medium", detail: "Data residency clause missing for JP data" },
          ].map((d, i) => (
            <div key={i} className={`rounded-lg border-l-4 p-3 ${d.severity === "high" ? "border-l-red-500 bg-red-50" : "border-l-yellow-500 bg-yellow-50"}`}>
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-900">{d.clause}</p>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${d.severity === "high" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>{d.severity}</span>
              </div>
              <p className="mt-1 text-xs text-gray-600">{d.contract}</p>
              <p className="mt-0.5 text-xs text-gray-500">{d.detail}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link href="/legal/contracts" className="rounded-xl border bg-white p-4 transition-colors hover:border-slate-300 hover:bg-slate-50">
          <p className="text-sm font-medium text-gray-900">Upload Contract</p>
          <p className="mt-1 text-xs text-gray-500">Submit a contract for automated clause analysis</p>
        </Link>
        <Link href="/legal/clauses" className="rounded-xl border bg-white p-4 transition-colors hover:border-slate-300 hover:bg-slate-50">
          <p className="text-sm font-medium text-gray-900">Search Clauses</p>
          <p className="mt-1 text-xs text-gray-500">Browse the standard clause library</p>
        </Link>
        <Link href="/legal/regulatory" className="rounded-xl border bg-white p-4 transition-colors hover:border-slate-300 hover:bg-slate-50">
          <p className="text-sm font-medium text-gray-900">View Regulatory Feed</p>
          <p className="mt-1 text-xs text-gray-500">Track upcoming regulatory changes and impacts</p>
        </Link>
      </div>
    </div>
  );
}
