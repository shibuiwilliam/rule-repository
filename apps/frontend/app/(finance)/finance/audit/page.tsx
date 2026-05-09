export default function AuditReportsPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Reports</h1>
        <p className="mt-1 text-sm text-gray-500">Financial compliance audit trails, evaluation histories, and remediation tracking</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { label: "Reports This Quarter", value: 12, color: "text-blue-600" },
          { label: "Findings Open", value: 3, color: "text-yellow-600" },
          { label: "Remediated", value: 9, color: "text-green-600" },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>
      <div className="rounded-xl border bg-white p-8 text-center text-sm text-gray-400">
        Connect to the evaluation audit log to generate reports. Configure the finance scope filters in the domain pack settings.
      </div>
    </div>
  );
}
