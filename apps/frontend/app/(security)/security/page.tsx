import Link from "next/link";

export default function SecurityDashboardPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Security Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Data classification, encryption status, and security posture overview</p>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Data Classification Overview</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
            <p className="text-3xl font-bold text-red-700">14</p>
            <p className="mt-1 text-sm text-red-600">Restricted</p>
          </div>
          <div className="rounded-lg border border-orange-200 bg-orange-50 p-4 text-center">
            <p className="text-3xl font-bold text-orange-700">47</p>
            <p className="mt-1 text-sm text-orange-600">Confidential</p>
          </div>
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
            <p className="text-3xl font-bold text-blue-700">156</p>
            <p className="mt-1 text-sm text-blue-600">Internal</p>
          </div>
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-center">
            <p className="text-3xl font-bold text-green-700">89</p>
            <p className="mt-1 text-sm text-green-600">Public</p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Encryption Key Status</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              <th className="px-5 py-3">Key ID</th>
              <th className="px-5 py-3">Purpose</th>
              <th className="px-5 py-3">Algorithm</th>
              <th className="px-5 py-3">Rotation Due</th>
              <th className="px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {[
              { id: "K-001", purpose: "Audit log encryption", alg: "AES-256-GCM", rotation: "2026-07-15", status: "active" },
              { id: "K-002", purpose: "PII field encryption", alg: "AES-256-GCM", rotation: "2026-08-01", status: "active" },
              { id: "K-003", purpose: "Evidence storage", alg: "AES-256-GCM", rotation: "2026-06-01", status: "rotation-due" },
              { id: "K-004", purpose: "API token signing", alg: "Ed25519", rotation: "2026-09-10", status: "active" },
            ].map((k) => (
              <tr key={k.id} className="hover:bg-gray-50">
                <td className="px-5 py-3 font-mono text-xs text-gray-500">{k.id}</td>
                <td className="px-5 py-3 font-medium text-gray-900">{k.purpose}</td>
                <td className="px-5 py-3 text-gray-600">{k.alg}</td>
                <td className="px-5 py-3 text-gray-500">{k.rotation}</td>
                <td className="px-5 py-3">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${k.status === "active" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>
                    {k.status === "rotation-due" ? "rotation due" : k.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Eval Harness Scores by Domain</h2>
        <p className="mt-1 text-xs text-gray-500">Latest nightly evaluation run results</p>
        <div className="mt-4 space-y-3">
          {[
            { domain: "Code Diff Evaluation", score: 94, tests: 212, passed: 199 },
            { domain: "Contract Clause Analysis", score: 87, tests: 85, passed: 74 },
            { domain: "HR Event Compliance", score: 91, tests: 56, passed: 51 },
            { domain: "Transaction Screening", score: 82, tests: 38, passed: 31 },
            { domain: "Creative Content Review", score: 78, tests: 24, passed: 19 },
          ].map((d) => (
            <div key={d.domain}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="text-gray-700">{d.domain}</span>
                <span className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{d.passed}/{d.tests}</span>
                  <span className={`font-medium ${d.score >= 90 ? "text-green-600" : d.score >= 80 ? "text-yellow-600" : "text-red-600"}`}>{d.score}%</span>
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                <div className={`h-full rounded-full ${d.score >= 90 ? "bg-green-500" : d.score >= 80 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${d.score}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Recent Access Log Entries</h2>
          <Link href="/security/access-logs" className="text-sm text-blue-600 hover:underline">View all</Link>
        </div>
        <div className="divide-y">
          {[
            { time: "09:42:15", user: "admin@company.co.jp", action: "Viewed RESTRICTED rule R-1401", result: "allowed" },
            { time: "09:38:02", user: "hr-manager@company.co.jp", action: "Exported CONFIDENTIAL audit packet", result: "allowed" },
            { time: "09:30:11", user: "intern@company.co.jp", action: "Attempted RESTRICTED rule access", result: "denied" },
            { time: "09:25:03", user: "legal@company.co.jp", action: "Downloaded regulator export (J-SOX)", result: "allowed" },
          ].map((entry, i) => (
            <div key={i} className="flex items-center gap-4 px-5 py-3">
              <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${entry.result === "allowed" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                {entry.result === "allowed" ? "\u2713" : "\u2717"}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-gray-700">{entry.action}</p>
                <p className="text-xs text-gray-400">{entry.user}</p>
              </div>
              <span className="text-xs text-gray-400">{entry.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
