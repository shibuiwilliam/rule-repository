export default function ControlsPage() {
  const controls = [
    { id: "CTRL-001", name: "Segregation of Duties", domain: "Accounts Payable", status: "effective", testDate: "2026-04-15", findings: 0 },
    { id: "CTRL-002", name: "Invoice Three-Way Match", domain: "Procurement", status: "effective", testDate: "2026-04-10", findings: 0 },
    { id: "CTRL-003", name: "Journal Entry Approval", domain: "General Ledger", status: "needs_remediation", testDate: "2026-04-20", findings: 2 },
    { id: "CTRL-004", name: "Budget Variance Review", domain: "Budgeting", status: "effective", testDate: "2026-03-30", findings: 0 },
    { id: "CTRL-005", name: "Tax Filing Compliance", domain: "Tax", status: "not_tested", testDate: "", findings: 0 },
    { id: "CTRL-006", name: "Petty Cash Reconciliation", domain: "Cash Management", status: "effective", testDate: "2026-05-01", findings: 1 },
  ];

  const statusBadge: Record<string, string> = {
    effective: "bg-green-100 text-green-800",
    needs_remediation: "bg-red-100 text-red-800",
    not_tested: "bg-gray-100 text-gray-700",
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Internal Controls</h1>
        <p className="mt-1 text-sm text-gray-500">Financial controls testing status, findings, and remediation tracking</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { label: "Controls Defined", value: controls.length, color: "text-blue-600" },
          { label: "Effective", value: controls.filter((c) => c.status === "effective").length, color: "text-green-600" },
          { label: "Open Findings", value: controls.reduce((a, c) => a + c.findings, 0), color: "text-red-600" },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-xl border bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs uppercase text-gray-500">
              <th className="px-5 py-3">Control</th>
              <th className="px-5 py-3">Domain</th>
              <th className="px-5 py-3">Last Tested</th>
              <th className="px-5 py-3">Findings</th>
              <th className="px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {controls.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-5 py-3 font-medium text-gray-900">{c.name}<br /><span className="text-xs text-gray-400">{c.id}</span></td>
                <td className="px-5 py-3 text-gray-600">{c.domain}</td>
                <td className="px-5 py-3 text-gray-600">{c.testDate || "Not tested"}</td>
                <td className="px-5 py-3">{c.findings > 0 ? <span className="text-red-600 font-medium">{c.findings}</span> : <span className="text-gray-400">0</span>}</td>
                <td className="px-5 py-3"><span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge[c.status]}`}>{c.status.replace("_", " ")}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
