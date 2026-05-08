"use client";

import { useState } from "react";

const USERS = [
  { id: "U-001", name: "Tanaka Yuki", email: "tanaka@acme.co.jp", roles: ["admin", "owner"], departments: ["Engineering"], lastActive: "2026-05-08 09:45", status: "active" as const, scimManaged: true },
  { id: "U-002", name: "Suzuki Hana", email: "suzuki@acme.co.jp", roles: ["reviewer", "owner"], departments: ["Legal"], lastActive: "2026-05-08 09:30", status: "active" as const, scimManaged: true },
  { id: "U-003", name: "Yamamoto Ken", email: "yamamoto@acme.co.jp", roles: ["reviewer"], departments: ["HR"], lastActive: "2026-05-07 17:20", status: "active" as const, scimManaged: true },
  { id: "U-004", name: "Sato Mei", email: "sato@acme.co.jp", roles: ["auditor"], departments: ["Finance", "Compliance"], lastActive: "2026-05-08 08:15", status: "active" as const, scimManaged: true },
  { id: "U-005", name: "Watanabe Ryo", email: "watanabe@acme.co.jp", roles: ["subscriber"], departments: ["Marketing"], lastActive: "2026-05-06 14:00", status: "active" as const, scimManaged: false },
  { id: "U-006", name: "Nakamura Taro", email: "nakamura@acme.co.jp", roles: ["reviewer"], departments: ["Sales"], lastActive: "-", status: "invited" as const, scimManaged: false },
];

const ROLE_BADGE: Record<string, string> = { admin: "bg-purple-100 text-purple-700", owner: "bg-blue-100 text-blue-700", reviewer: "bg-green-100 text-green-700", auditor: "bg-amber-100 text-amber-700", subscriber: "bg-gray-100 text-gray-600" };
const STATUS_BADGE: Record<string, string> = { active: "bg-green-100 text-green-700", inactive: "bg-gray-100 text-gray-600", invited: "bg-blue-100 text-blue-700" };

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const filtered = USERS.filter((u) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
        <p className="mt-1 text-sm text-gray-500">Manage users, roles, and department assignments</p>
      </div>

      <div className="flex items-center gap-3 rounded-xl border bg-white p-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100"><span className="h-3 w-3 rounded-full bg-green-500" /></span>
        <div>
          <p className="text-sm font-medium text-gray-900">SCIM Sync Active</p>
          <p className="text-xs text-gray-500">Last sync: 2026-05-08 09:00 | Provider: Azure AD</p>
        </div>
      </div>

      <input type="text" placeholder="Search by name or email..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full rounded-lg border bg-white px-4 py-2 text-sm text-gray-700 placeholder:text-gray-400" />

      <div className="rounded-xl border bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              <th className="px-5 py-3">User</th>
              <th className="px-5 py-3">Roles</th>
              <th className="px-5 py-3">Departments</th>
              <th className="px-5 py-3">Last Active</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-5 py-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-600">{u.name.split(" ").map((n) => n[0]).join("")}</div>
                    <div>
                      <p className="font-medium text-gray-900">{u.name}</p>
                      <p className="text-xs text-gray-400">{u.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <div className="flex flex-wrap gap-1">
                    {u.roles.map((r) => <span key={r} className={`rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_BADGE[r] ?? "bg-gray-100"}`}>{r}</span>)}
                  </div>
                </td>
                <td className="px-5 py-3 text-gray-600">{u.departments.join(", ")}</td>
                <td className="px-5 py-3 text-gray-500">{u.lastActive}</td>
                <td className="px-5 py-3"><span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[u.status]}`}>{u.status}</span></td>
                <td className="px-5 py-3"><span className={`text-xs ${u.scimManaged ? "text-blue-600" : "text-gray-400"}`}>{u.scimManaged ? "SCIM" : "Manual"}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
