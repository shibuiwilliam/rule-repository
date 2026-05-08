import Link from "next/link";

const BUNDLES = [
  { id: "B-001", name: "J-SOX Internal Controls", framework: "J-SOX", totalControls: 42, implementedControls: 38, lastAudit: "2026-04-15", status: "on-track" as const },
  { id: "B-002", name: "GDPR Data Protection", framework: "GDPR", totalControls: 35, implementedControls: 28, lastAudit: "2026-03-20", status: "at-risk" as const },
  { id: "B-003", name: "EU AI Act Compliance", framework: "EU AI Act", totalControls: 18, implementedControls: 8, lastAudit: "2026-04-01", status: "behind" as const },
  { id: "B-004", name: "ISO 27001 Security", framework: "ISO 27001", totalControls: 93, implementedControls: 87, lastAudit: "2026-04-28", status: "on-track" as const },
];

const EXCEPTIONS = [
  { id: "EX-101", rule: "All PII must be encrypted at rest", department: "Engineering", reason: "Legacy migration in progress", grantedBy: "CISO", expiresAt: "2026-06-30", status: "active" as const },
  { id: "EX-102", rule: "Overtime must not exceed 45h/month", department: "Operations", reason: "Seasonal peak processing", grantedBy: "HR Director", expiresAt: "2026-05-31", status: "pending-renewal" as const },
  { id: "EX-103", rule: "Vendor payments require dual approval", department: "Finance", reason: "Temporary staffing shortage", grantedBy: "CFO", expiresAt: "2026-05-15", status: "active" as const },
];

const STATUS_BADGE: Record<string, string> = {
  "on-track": "bg-green-100 text-green-700", "at-risk": "bg-yellow-100 text-yellow-700", behind: "bg-red-100 text-red-700",
  active: "bg-green-100 text-green-700", "pending-renewal": "bg-yellow-100 text-yellow-700",
};

export default function ComplianceDashboardPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Compliance Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Framework progress, control status, and exception management</p>
      </div>

      <div>
        <h2 className="mb-3 text-base font-semibold text-gray-900">Bundle Progress</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {BUNDLES.map((b) => {
            const pct = Math.round((b.implementedControls / b.totalControls) * 100);
            return (
              <div key={b.id} className="rounded-xl border bg-white p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">{b.name}</h3>
                    <p className="text-xs text-gray-500">{b.framework}</p>
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[b.status]}`}>{b.status.replace("-", " ")}</span>
                </div>
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">{b.implementedControls}/{b.totalControls} controls</span>
                    <span className="font-medium text-gray-900">{pct}%</span>
                  </div>
                  <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-gray-100">
                    <div className={`h-full rounded-full ${pct >= 90 ? "bg-green-500" : pct >= 70 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${pct}%` }} />
                  </div>
                  <p className="mt-2 text-xs text-gray-400">Last audit: {b.lastAudit}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Control Framework Status</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-center">
            <p className="text-3xl font-bold text-green-700">161</p>
            <p className="mt-1 text-sm text-green-600">Implemented</p>
          </div>
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-center">
            <p className="text-3xl font-bold text-yellow-700">16</p>
            <p className="mt-1 text-sm text-yellow-600">In Progress</p>
          </div>
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
            <p className="text-3xl font-bold text-red-700">11</p>
            <p className="mt-1 text-sm text-red-600">Not Started</p>
          </div>
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
            <p className="text-3xl font-bold text-blue-700">3</p>
            <p className="mt-1 text-sm text-blue-600">Exceptions</p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Exception Queue</h2>
          <Link href="/compliance/exceptions" className="text-sm text-blue-600 hover:underline">View all</Link>
        </div>
        <div className="divide-y">
          {EXCEPTIONS.map((ex) => (
            <div key={ex.id} className="flex items-start gap-4 px-5 py-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">{ex.rule}</p>
                <p className="mt-0.5 text-xs text-gray-500">{ex.department} | Granted by {ex.grantedBy} | Expires {ex.expiresAt}</p>
                <p className="mt-0.5 text-xs text-gray-400">Reason: {ex.reason}</p>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[ex.status]}`}>{ex.status.replace("-", " ")}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Regulatory Horizon</h2>
        <div className="mt-4 space-y-3">
          {[
            { date: "2026-06-15", event: "Updated Subcontract Act enforcement standards", impact: "medium" },
            { date: "2026-07-01", event: "Revised APPI Guidelines effective", impact: "high" },
            { date: "2026-08-01", event: "EU AI Act - High-Risk System Requirements", impact: "high" },
            { date: "2026-12-31", event: "J-SOX annual reporting deadline", impact: "high" },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-4 rounded-lg border p-3">
              <div className="w-20 text-center">
                <p className="text-xs font-semibold text-gray-900">{item.date.split("-").slice(1).join("/")}</p>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-gray-700">{item.event}</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${item.impact === "high" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>{item.impact}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
