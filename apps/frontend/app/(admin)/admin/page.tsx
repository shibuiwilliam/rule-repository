import Link from "next/link";

export default function AdminDashboardPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">System overview, tenant management, and platform health</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Active Tenants</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">8</p>
          <p className="mt-1 text-xs text-gray-400">2 trial, 6 production</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Total Rules</p>
          <p className="mt-1 text-3xl font-bold text-blue-600">1,247</p>
          <p className="mt-1 text-xs text-gray-400">Across all tenants</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Evaluations Today</p>
          <p className="mt-1 text-3xl font-bold text-green-600">3,842</p>
          <p className="mt-1 text-xs text-gray-400">+12% vs. yesterday</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Active Users</p>
          <p className="mt-1 text-3xl font-bold text-purple-600">124</p>
          <p className="mt-1 text-xs text-gray-400">Last 24 hours</p>
        </div>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">System Health</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { service: "API Server", status: "healthy", latency: "12ms", uptime: "99.98%" },
            { service: "PostgreSQL", status: "healthy", latency: "3ms", uptime: "99.99%" },
            { service: "Elasticsearch", status: "healthy", latency: "8ms", uptime: "99.95%" },
            { service: "Neo4j", status: "healthy", latency: "5ms", uptime: "99.97%" },
            { service: "Redis", status: "healthy", latency: "1ms", uptime: "99.99%" },
            { service: "arq Worker", status: "degraded", latency: "45ms", uptime: "99.80%" },
          ].map((s) => (
            <div key={s.service} className="flex items-center gap-3 rounded-lg border p-3">
              <span className={`flex h-8 w-8 items-center justify-center rounded-full ${s.status === "healthy" ? "bg-green-100" : "bg-yellow-100"}`}>
                <span className={`h-3 w-3 rounded-full ${s.status === "healthy" ? "bg-green-500" : "bg-yellow-500"}`} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">{s.service}</p>
                <p className="text-xs text-gray-400">{s.latency} avg | {s.uptime} uptime</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">User Activity Summary</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              <th className="px-5 py-3">Tenant</th>
              <th className="px-5 py-3">Active Users</th>
              <th className="px-5 py-3">Evaluations (24h)</th>
              <th className="px-5 py-3">Rules</th>
              <th className="px-5 py-3">Plan</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {[
              { tenant: "Acme Corp", users: 45, evals: 1240, rules: 312, plan: "Enterprise" },
              { tenant: "TechStart Inc.", users: 22, evals: 820, rules: 156, plan: "Business" },
              { tenant: "Global Finance", users: 18, evals: 650, rules: 245, plan: "Enterprise" },
              { tenant: "NewCo (Trial)", users: 5, evals: 42, rules: 18, plan: "Trial" },
            ].map((t) => (
              <tr key={t.tenant} className="hover:bg-gray-50">
                <td className="px-5 py-3 font-medium text-gray-900">{t.tenant}</td>
                <td className="px-5 py-3 text-gray-600">{t.users}</td>
                <td className="px-5 py-3 text-gray-600">{t.evals.toLocaleString()}</td>
                <td className="px-5 py-3 text-gray-600">{t.rules}</td>
                <td className="px-5 py-3">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${t.plan === "Enterprise" ? "bg-purple-100 text-purple-700" : t.plan === "Business" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"}`}>{t.plan}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link href="/admin/tenants" className="rounded-xl border bg-white p-4 transition-colors hover:border-gray-300 hover:bg-gray-50">
          <p className="text-sm font-medium text-gray-900">Add Tenant</p>
          <p className="mt-1 text-xs text-gray-500">Provision a new organization tenant</p>
        </Link>
        <Link href="/admin/settings" className="rounded-xl border bg-white p-4 transition-colors hover:border-gray-300 hover:bg-gray-50">
          <p className="text-sm font-medium text-gray-900">Configure SSO</p>
          <p className="mt-1 text-xs text-gray-500">Set up SAML/OIDC identity provider</p>
        </Link>
        <Link href="/admin/connectors" className="rounded-xl border bg-white p-4 transition-colors hover:border-gray-300 hover:bg-gray-50">
          <p className="text-sm font-medium text-gray-900">Manage Connectors</p>
          <p className="mt-1 text-xs text-gray-500">Configure HRIS, ERP, and document source integrations</p>
        </Link>
      </div>
    </div>
  );
}
