"use client";

import { useState } from "react";

const TENANTS = [
  { id: "T-001", name: "Acme Corp", plan: "enterprise", status: "active", ruleCount: 312, userCount: 45, createdAt: "2025-06-15", domain: "acme.co.jp" },
  { id: "T-002", name: "TechStart Inc.", plan: "business", status: "active", ruleCount: 156, userCount: 22, createdAt: "2025-09-01", domain: "techstart.io" },
  { id: "T-003", name: "Global Finance", plan: "enterprise", status: "active", ruleCount: 245, userCount: 18, createdAt: "2025-07-20", domain: "globalfin.com" },
  { id: "T-004", name: "RetailMax", plan: "business", status: "suspended", ruleCount: 67, userCount: 8, createdAt: "2026-01-15", domain: "retailmax.co.jp" },
  { id: "T-005", name: "NewCo", plan: "trial", status: "trial", ruleCount: 18, userCount: 5, createdAt: "2026-04-28", domain: "newco.dev" },
];

const PLAN_BADGE: Record<string, string> = { enterprise: "bg-purple-100 text-purple-700", business: "bg-blue-100 text-blue-700", trial: "bg-gray-100 text-gray-600" };
const STATUS_BADGE: Record<string, string> = { active: "bg-green-100 text-green-700", suspended: "bg-red-100 text-red-700", trial: "bg-yellow-100 text-yellow-700" };

export default function TenantsPage() {
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tenant Management</h1>
          <p className="mt-1 text-sm text-gray-500">Manage organization tenants, plans, and configurations</p>
        </div>
        <button type="button" onClick={() => setShowForm(!showForm)} className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">Add Tenant</button>
      </div>

      {showForm && (
        <div className="rounded-xl border bg-white p-5">
          <h2 className="text-base font-semibold text-gray-900">Create New Tenant</h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="t-name" className="block text-sm font-medium text-gray-700">Organization Name</label>
              <input id="t-name" type="text" placeholder="Enter name" className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm" />
            </div>
            <div>
              <label htmlFor="t-domain" className="block text-sm font-medium text-gray-700">Domain</label>
              <input id="t-domain" type="text" placeholder="company.com" className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm" />
            </div>
            <div>
              <label htmlFor="t-plan" className="block text-sm font-medium text-gray-700">Plan</label>
              <select id="t-plan" className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm">
                <option value="trial">Trial</option>
                <option value="business">Business</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </div>
            <div>
              <label htmlFor="t-email" className="block text-sm font-medium text-gray-700">Admin Email</label>
              <input id="t-email" type="email" placeholder="admin@company.com" className="mt-1 block w-full rounded-lg border px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button type="button" className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">Create</button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="rounded-xl border bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              <th className="px-5 py-3">Organization</th>
              <th className="px-5 py-3">Domain</th>
              <th className="px-5 py-3">Plan</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Rules</th>
              <th className="px-5 py-3">Users</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {TENANTS.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-5 py-3 font-medium text-gray-900">{t.name}</td>
                <td className="px-5 py-3 text-gray-600">{t.domain}</td>
                <td className="px-5 py-3"><span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${PLAN_BADGE[t.plan]}`}>{t.plan}</span></td>
                <td className="px-5 py-3"><span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[t.status]}`}>{t.status}</span></td>
                <td className="px-5 py-3 text-gray-600">{t.ruleCount}</td>
                <td className="px-5 py-3 text-gray-600">{t.userCount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
