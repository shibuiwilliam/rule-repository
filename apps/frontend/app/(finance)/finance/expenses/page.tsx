"use client";

interface ExpensePolicy {
  id: string;
  title: string;
  category: string;
  limit: string;
  approvalRequired: string;
  activeRules: number;
  violationsThisMonth: number;
  lastUpdated: string;
}

const POLICIES: ExpensePolicy[] = [
  { id: "EXP-001", title: "Domestic Travel Expenses", category: "Travel", limit: "JPY 50,000/trip", approvalRequired: "Department head", activeRules: 4, violationsThisMonth: 2, lastUpdated: "2026-04-01" },
  { id: "EXP-002", title: "International Travel Expenses", category: "Travel", limit: "JPY 300,000/trip", approvalRequired: "Division head + Finance", activeRules: 6, violationsThisMonth: 0, lastUpdated: "2026-03-15" },
  { id: "EXP-003", title: "Client Entertainment", category: "Entertainment", limit: "JPY 30,000/event", approvalRequired: "Department head", activeRules: 3, violationsThisMonth: 1, lastUpdated: "2026-04-10" },
  { id: "EXP-004", title: "Office Supplies and Equipment", category: "Supplies", limit: "JPY 100,000/item", approvalRequired: "Manager (dual for >JPY 100K)", activeRules: 2, violationsThisMonth: 0, lastUpdated: "2026-02-20" },
  { id: "EXP-005", title: "Training and Education", category: "Development", limit: "JPY 200,000/year/person", approvalRequired: "Department head + HR", activeRules: 3, violationsThisMonth: 0, lastUpdated: "2026-01-10" },
  { id: "EXP-006", title: "Software and SaaS Subscriptions", category: "IT", limit: "JPY 500,000/year/tool", approvalRequired: "IT + Finance", activeRules: 4, violationsThisMonth: 3, lastUpdated: "2026-04-25" },
];

export default function ExpensePolicyPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Expense Policies</h1>
        <p className="mt-1 text-sm text-gray-500">Spending limits, approval requirements, and violation tracking by category</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "Policies", value: POLICIES.length, color: "text-blue-600" },
          { label: "Active Rules", value: POLICIES.reduce((a, p) => a + p.activeRules, 0), color: "text-green-600" },
          { label: "Violations This Month", value: POLICIES.reduce((a, p) => a + p.violationsThisMonth, 0), color: "text-red-600" },
          { label: "Categories", value: new Set(POLICIES.map((p) => p.category)).size, color: "text-purple-600" },
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
              <th className="px-5 py-3">Policy</th>
              <th className="px-5 py-3">Category</th>
              <th className="px-5 py-3">Limit</th>
              <th className="px-5 py-3">Approval</th>
              <th className="px-5 py-3">Rules</th>
              <th className="px-5 py-3">Violations</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {POLICIES.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-5 py-3 font-medium text-gray-900">{p.title}</td>
                <td className="px-5 py-3"><span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-600">{p.category}</span></td>
                <td className="px-5 py-3 text-gray-600">{p.limit}</td>
                <td className="px-5 py-3 text-xs text-gray-600">{p.approvalRequired}</td>
                <td className="px-5 py-3 text-gray-600">{p.activeRules}</td>
                <td className="px-5 py-3">{p.violationsThisMonth > 0 ? <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">{p.violationsThisMonth}</span> : <span className="text-gray-400">0</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
