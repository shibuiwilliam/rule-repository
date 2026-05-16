"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

type RiskLevel = "critical" | "warning" | "normal";

interface DeptOvertime {
  department: string;
  avgHours: number;
  maxHours: number;
  employeesOverLimit: number;
  totalEmployees: number;
}

interface EmployeeRisk {
  id: string;
  name: string;
  department: string;
  currentHours: number;
  limit: number;
  risk: RiskLevel;
}

interface AgreementStatus {
  department: string;
  hasAgreement: boolean;
  specialExtension: boolean;
  maxAllowed: number;
  expiry: string;
}

const RISK_BADGE: Record<RiskLevel, string> = {
  critical: "bg-red-100 text-red-700",
  warning: "bg-yellow-100 text-yellow-700",
  normal: "bg-green-100 text-green-700",
};

export default function AttendancePage() {
  const [deptOvertime, setDeptOvertime] = useState<DeptOvertime[]>([]);
  const [employeeRisks, setEmployeeRisks] = useState<EmployeeRisk[]>([]);
  const [agreementStatus, setAgreementStatus] = useState<AgreementStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDept, setSelectedDept] = useState<string>("all");
  const [selectedMonth, setSelectedMonth] = useState<string>("2026-05");
  const [selectedRisk, setSelectedRisk] = useState<string>("all");

  useEffect(() => {
    fetchSeedData<{ attendance: { dept_overtime: DeptOvertime[]; employee_risks: EmployeeRisk[]; agreement_status: AgreementStatus[] } }>("hr").then((d) => {
      setDeptOvertime(d.attendance?.dept_overtime ?? []);
      setEmployeeRisks(d.attendance?.employee_risks ?? []);
      setAgreementStatus(d.attendance?.agreement_status ?? []);
      setLoading(false);
    });
  }, []);

  const filteredEmployees = employeeRisks.filter((e) => {
    if (selectedDept !== "all" && e.department !== selectedDept) return false;
    if (selectedRisk !== "all" && e.risk !== selectedRisk) return false;
    return true;
  });

  const departments = [...new Set(deptOvertime.map((d) => d.department))];

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Attendance Compliance</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overtime monitoring, 36-agreement status, and employee risk tracking
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <label htmlFor="dept-filter" className="text-xs font-medium text-gray-500">Department</label>
          <select
            id="dept-filter"
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            className="mt-0.5 block rounded-lg border bg-white px-3 py-1.5 text-sm text-gray-700"
          >
            <option value="all">All Departments</option>
            {departments.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="month-filter" className="text-xs font-medium text-gray-500">Month</label>
          <input
            id="month-filter"
            type="month"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="mt-0.5 block rounded-lg border bg-white px-3 py-1.5 text-sm text-gray-700"
          />
        </div>
        <div>
          <label htmlFor="risk-filter" className="text-xs font-medium text-gray-500">Risk Level</label>
          <select
            id="risk-filter"
            value={selectedRisk}
            onChange={(e) => setSelectedRisk(e.target.value)}
            className="mt-0.5 block rounded-lg border bg-white px-3 py-1.5 text-sm text-gray-700"
          >
            <option value="all">All Levels</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="normal">Normal</option>
          </select>
        </div>
      </div>

      {/* Monthly overtime summary */}
      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Monthly Overtime Summary by Department</h2>
          <p className="text-xs text-gray-500">{selectedMonth}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">Department</th>
                <th className="px-5 py-3">Avg Hours</th>
                <th className="px-5 py-3">Max Hours</th>
                <th className="px-5 py-3">Over Limit</th>
                <th className="px-5 py-3">Total</th>
                <th className="px-5 py-3">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {deptOvertime.filter((d) => selectedDept === "all" || d.department === selectedDept).map((d) => (
                <tr key={d.department} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">{d.department}</td>
                  <td className="px-5 py-3 text-gray-600">{d.avgHours}h</td>
                  <td className="px-5 py-3 text-gray-600">{d.maxHours}h</td>
                  <td className="px-5 py-3">
                    <span className={d.employeesOverLimit > 0 ? "font-semibold text-red-600" : "text-green-600"}>
                      {d.employeesOverLimit}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-600">{d.totalEmployees}</td>
                  <td className="px-5 py-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      d.employeesOverLimit > 2 ? "bg-red-100 text-red-700" : d.employeesOverLimit > 0 ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-700"
                    }`}>
                      {d.employeesOverLimit > 2 ? "High" : d.employeesOverLimit > 0 ? "Medium" : "Low"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Employee risk list */}
      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Employee Risk List</h2>
          <p className="text-xs text-gray-500">Employees near or over monthly overtime limits</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Department</th>
                <th className="px-5 py-3">Current</th>
                <th className="px-5 py-3">Limit</th>
                <th className="px-5 py-3">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredEmployees.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs text-gray-500">{e.id}</td>
                  <td className="px-5 py-3 font-medium text-gray-900">{e.name}</td>
                  <td className="px-5 py-3 text-gray-600">{e.department}</td>
                  <td className="px-5 py-3">
                    <span className={e.currentHours > e.limit ? "font-semibold text-red-600" : "text-gray-700"}>
                      {e.currentHours}h
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-500">{e.limit}h</td>
                  <td className="px-5 py-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${RISK_BADGE[e.risk]}`}>
                      {e.risk}
                    </span>
                  </td>
                </tr>
              ))}
              {filteredEmployees.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-sm text-gray-400">
                    No employees match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 36-Agreement status */}
      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">36-Agreement Status</h2>
          <p className="text-xs text-gray-500">Labor Standards Act Article 36 agreement overview</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">Department</th>
                <th className="px-5 py-3">Agreement</th>
                <th className="px-5 py-3">Special Extension</th>
                <th className="px-5 py-3">Max Allowed</th>
                <th className="px-5 py-3">Expiry</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {agreementStatus.map((a) => (
                <tr key={a.department} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-medium text-gray-900">{a.department}</td>
                  <td className="px-5 py-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${a.hasAgreement ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                      {a.hasAgreement ? "Active" : "Missing"}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-600">{a.specialExtension ? "Yes" : "No"}</td>
                  <td className="px-5 py-3 text-gray-700">{a.maxAllowed}h/month</td>
                  <td className="px-5 py-3 text-gray-500">{a.expiry}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
