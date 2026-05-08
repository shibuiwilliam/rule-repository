import Link from "next/link";

export default function FinanceDashboardPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Finance Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Expense compliance, invoice validation, and financial controls</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Active Finance Rules</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">42</p>
          <p className="mt-1 text-xs text-gray-400">5 pending review</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Expense Violations (MTD)</p>
          <p className="mt-1 text-3xl font-bold text-red-600">8</p>
          <p className="mt-1 text-xs text-gray-400">Approval threshold breaches</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Evaluations Today</p>
          <p className="mt-1 text-3xl font-bold text-blue-600">156</p>
          <p className="mt-1 text-xs text-gray-400">Transaction screenings</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">J-SOX Compliance</p>
          <p className="mt-1 text-3xl font-bold text-green-600">94%</p>
          <p className="mt-1 text-xs text-gray-400">38/42 controls implemented</p>
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Recent Transaction Screenings</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">Transaction ID</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">Amount</th>
                <th className="px-5 py-3">Vendor</th>
                <th className="px-5 py-3">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {[
                { id: "TXN-4501", type: "Expense Claim", amount: "JPY 245,000", vendor: "AWS", result: "allow" },
                { id: "TXN-4502", type: "Invoice Payment", amount: "JPY 1,200,000", vendor: "Recruit Co.", result: "deny" },
                { id: "TXN-4503", type: "Expense Claim", amount: "JPY 85,000", vendor: "Travel", result: "allow" },
                { id: "TXN-4504", type: "Purchase Order", amount: "JPY 3,500,000", vendor: "Hardware Vendor", result: "needs_confirmation" },
              ].map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs text-gray-500">{t.id}</td>
                  <td className="px-5 py-3 text-gray-600">{t.type}</td>
                  <td className="px-5 py-3 font-medium text-gray-900">{t.amount}</td>
                  <td className="px-5 py-3 text-gray-600">{t.vendor}</td>
                  <td className="px-5 py-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      t.result === "allow" ? "bg-green-100 text-green-700" : t.result === "deny" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                    }`}>{t.result}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link href="/finance/expenses" className="rounded-xl border bg-white p-4 transition-colors hover:border-emerald-300 hover:bg-emerald-50">
          <p className="text-sm font-medium text-gray-900">Expense Policy</p>
          <p className="mt-1 text-xs text-gray-500">Review expense rules and approval thresholds</p>
        </Link>
        <Link href="/finance/audit" className="rounded-xl border bg-white p-4 transition-colors hover:border-emerald-300 hover:bg-emerald-50">
          <p className="text-sm font-medium text-gray-900">Audit Reports</p>
          <p className="mt-1 text-xs text-gray-500">J-SOX and financial audit evidence export</p>
        </Link>
        <Link href="/finance/controls" className="rounded-xl border bg-white p-4 transition-colors hover:border-emerald-300 hover:bg-emerald-50">
          <p className="text-sm font-medium text-gray-900">Financial Controls</p>
          <p className="mt-1 text-xs text-gray-500">Segregation of duties and approval workflows</p>
        </Link>
      </div>
    </div>
  );
}
