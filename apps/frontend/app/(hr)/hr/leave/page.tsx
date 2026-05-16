"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface DeptLeave {
  department: string;
  totalEmployees: number;
  avgBalance: number;
  compulsoryMet: number;
  compulsoryTotal: number;
}

interface LeaveRequest {
  id: string;
  employee: string;
  department: string;
  type: string;
  startDate: string;
  endDate: string;
  days: number;
  status: "pending" | "approved" | "denied";
}

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  denied: "bg-red-100 text-red-700",
};

export default function LeavePage() {
  const [deptLeave, setDeptLeave] = useState<DeptLeave[]>([]);
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ leave: { dept_leave: DeptLeave[]; leave_requests: LeaveRequest[] } }>("hr").then((d) => {
      setDeptLeave(d.leave?.dept_leave ?? []);
      setLeaveRequests(d.leave?.leave_requests ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Leave Management</h1>
        <p className="mt-1 text-sm text-gray-500">
          Leave balances, compulsory leave compliance, and pending requests
        </p>
      </div>

      {/* Leave balance overview */}
      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Leave Balance Overview by Department</h2>
        </div>
        <div className="grid grid-cols-1 gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3">
          {deptLeave.map((d) => {
            const pct = Math.round((d.compulsoryMet / d.compulsoryTotal) * 100);
            return (
              <div key={d.department} className="rounded-lg border p-4">
                <h3 className="text-sm font-semibold text-gray-900">{d.department}</h3>
                <div className="mt-3 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Employees</span>
                    <span className="font-medium">{d.totalEmployees}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Avg Balance</span>
                    <span className="font-medium">{d.avgBalance} days</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Compulsory Met</span>
                    <span className={`font-medium ${pct === 100 ? "text-green-600" : "text-yellow-600"}`}>
                      {d.compulsoryMet}/{d.compulsoryTotal} ({pct}%)
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-100">
                    <div
                      className={`h-full rounded-full ${pct === 100 ? "bg-green-500" : "bg-yellow-500"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Compulsory leave compliance */}
      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Compulsory Leave Compliance</h2>
        <p className="mt-1 text-xs text-gray-500">
          Employees with 10+ days annual leave entitlement must take at least 5 days per year (Labor Standards Act)
        </p>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-center">
            <p className="text-3xl font-bold text-green-700">105</p>
            <p className="mt-1 text-sm text-green-600">Compliant</p>
          </div>
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-center">
            <p className="text-3xl font-bold text-yellow-700">14</p>
            <p className="mt-1 text-sm text-yellow-600">At Risk (under 3 days taken)</p>
          </div>
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
            <p className="text-3xl font-bold text-red-700">5</p>
            <p className="mt-1 text-sm text-red-600">Non-Compliant (0 days taken)</p>
          </div>
        </div>
      </div>

      {/* Leave request queue */}
      <div className="rounded-xl border bg-white">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Leave Request Queue</h2>
          <span className="rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-700">
            3 pending
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Employee</th>
                <th className="px-5 py-3">Department</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">Period</th>
                <th className="px-5 py-3">Days</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {leaveRequests.map((lr) => (
                <tr key={lr.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs text-gray-500">{lr.id}</td>
                  <td className="px-5 py-3 font-medium text-gray-900">{lr.employee}</td>
                  <td className="px-5 py-3 text-gray-600">{lr.department}</td>
                  <td className="px-5 py-3 text-gray-600">{lr.type}</td>
                  <td className="px-5 py-3 text-gray-600">{lr.startDate} - {lr.endDate}</td>
                  <td className="px-5 py-3 text-gray-700">{lr.days}</td>
                  <td className="px-5 py-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[lr.status]}`}>
                      {lr.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
