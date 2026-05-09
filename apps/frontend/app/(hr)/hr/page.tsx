import Link from "next/link";

function StatCard({
  label,
  value,
  trend,
  color = "text-gray-900",
}: {
  label: string;
  value: string | number;
  trend?: string;
  color?: string;
}) {
  return (
    <div className="rounded-xl border bg-white p-5">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${color}`}>{value}</p>
      {trend && <p className="mt-1 text-xs text-gray-400">{trend}</p>}
    </div>
  );
}

const RECENT_VIOLATIONS = [
  { id: "V-001", employee: "Dept: Engineering", rule: "Monthly overtime must not exceed 45 hours", date: "2026-05-07" },
  { id: "V-002", employee: "Dept: Sales", rule: "Minimum 5 annual leave days must be taken per year", date: "2026-05-06" },
  { id: "V-003", employee: "Dept: Marketing", rule: "36-agreement special extension requires prior approval", date: "2026-05-05" },
  { id: "V-004", employee: "Dept: Operations", rule: "Midnight work (22:00-05:00) requires health check", date: "2026-05-04" },
];

export default function HrDashboardPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">HR Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Labor compliance overview and workforce risk indicators
        </p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Overtime Violations (MTD)" value={12} color="text-red-600" trend="+3 from last month" />
        <StatCard label="Leave Compliance Rate" value="87%" color="text-yellow-600" trend="Target: 100%" />
        <StatCard label="Upcoming Reviews" value={8} trend="Next 14 days" />
        <StatCard label="Active HR Rules" value={34} trend="6 pending review" />
      </div>

      {/* Recent violations table */}
      <div className="rounded-xl border bg-white">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Recent Violations</h2>
          <Link href="/hr/reports" className="text-sm text-blue-600 hover:underline">
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Department</th>
                <th className="px-5 py-3">Rule</th>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {RECENT_VIOLATIONS.map((v) => (
                <tr key={v.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">{v.id}</td>
                  <td className="px-5 py-3 text-gray-600">{v.employee}</td>
                  <td className="max-w-xs truncate px-5 py-3 text-gray-700">{v.rule}</td>
                  <td className="px-5 py-3 text-gray-500">{v.date}</td>
                  <td className="px-5 py-3">
                    <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
                      Open
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Department breakdown */}
      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Violations by Department</h2>
        <div className="mt-4 space-y-3">
          {[
            { dept: "Engineering", count: 5, pct: 42 },
            { dept: "Sales", count: 3, pct: 25 },
            { dept: "Marketing", count: 2, pct: 17 },
            { dept: "Operations", count: 2, pct: 17 },
          ].map((d) => (
            <div key={d.dept}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="text-gray-700">{d.dept}</span>
                <span className="text-gray-500">{d.count} violations</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                <div className="h-full rounded-full bg-indigo-500" style={{ width: `${d.pct}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link
          href="/hr/attendance"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-indigo-300 hover:bg-indigo-50"
        >
          <p className="text-sm font-medium text-gray-900">Check Employee</p>
          <p className="mt-1 text-xs text-gray-500">Evaluate an employee event against HR rules</p>
        </Link>
        <Link
          href="/hr/policies"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-indigo-300 hover:bg-indigo-50"
        >
          <p className="text-sm font-medium text-gray-900">Review Policy</p>
          <p className="mt-1 text-xs text-gray-500">Browse and update HR policy rules</p>
        </Link>
        <Link
          href="/hr/hris"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-indigo-300 hover:bg-indigo-50"
        >
          <p className="text-sm font-medium text-gray-900">HRIS Sync Status</p>
          <p className="mt-1 text-xs text-gray-500">Check HRIS sync status</p>
        </Link>
      </div>
    </div>
  );
}
