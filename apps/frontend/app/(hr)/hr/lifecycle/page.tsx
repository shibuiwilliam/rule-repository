"use client";

import { useState } from "react";

type EventType = "all" | "onboarding" | "transfer" | "promotion" | "leave" | "termination";

interface LifecycleEvent {
  id: string;
  employeeId: string;
  employeeName: string;
  department: string;
  eventType: Exclude<EventType, "all">;
  description: string;
  date: string;
  complianceStatus: "compliant" | "warning" | "violation";
  rulesChecked: number;
  flaggedRules: number;
}

const EVENTS: LifecycleEvent[] = [
  { id: "EVT-001", employeeId: "E-1042", employeeName: "A. Suzuki", department: "Engineering", eventType: "onboarding", description: "New hire onboarding - Senior Backend Engineer", date: "2026-05-08", complianceStatus: "compliant", rulesChecked: 12, flaggedRules: 0 },
  { id: "EVT-002", employeeId: "E-0831", employeeName: "K. Watanabe", department: "Sales", eventType: "transfer", description: "Transfer from Tokyo HQ to Osaka branch", date: "2026-05-07", complianceStatus: "warning", rulesChecked: 8, flaggedRules: 1 },
  { id: "EVT-003", employeeId: "E-0215", employeeName: "M. Tanaka", department: "Finance", eventType: "promotion", description: "Promotion to Finance Manager - requires updated signing authority", date: "2026-05-05", complianceStatus: "compliant", rulesChecked: 15, flaggedRules: 0 },
  { id: "EVT-004", employeeId: "E-0567", employeeName: "T. Nakamura", department: "Legal", eventType: "leave", description: "Child-care leave application - 6 months", date: "2026-05-04", complianceStatus: "compliant", rulesChecked: 10, flaggedRules: 0 },
  { id: "EVT-005", employeeId: "E-1103", employeeName: "S. Kim", department: "Marketing", eventType: "termination", description: "Voluntary resignation - 30-day notice period", date: "2026-05-02", complianceStatus: "violation", rulesChecked: 9, flaggedRules: 2 },
  { id: "EVT-006", employeeId: "E-0923", employeeName: "R. Yamamoto", department: "Engineering", eventType: "transfer", description: "Transfer to overseas subsidiary (Singapore)", date: "2026-04-28", complianceStatus: "warning", rulesChecked: 18, flaggedRules: 3 },
];

const EVENT_TYPE_LABELS: Record<EventType, string> = {
  all: "All Events", onboarding: "Onboarding", transfer: "Transfer",
  promotion: "Promotion", leave: "Leave", termination: "Termination",
};

const EVENT_TYPE_ICON: Record<string, string> = {
  onboarding: "\uD83D\uDFE2", transfer: "\uD83D\uDD04", promotion: "\u2B06\uFE0F",
  leave: "\uD83C\uDFD6\uFE0F", termination: "\uD83D\uDFE5",
};

const STATUS_BADGE: Record<string, string> = {
  compliant: "bg-green-100 text-green-800",
  warning: "bg-yellow-100 text-yellow-800",
  violation: "bg-red-100 text-red-800",
};

export default function LifecyclePage() {
  const [typeFilter, setTypeFilter] = useState<EventType>("all");
  const [search, setSearch] = useState("");

  const filtered = EVENTS.filter((e) => {
    if (typeFilter !== "all" && e.eventType !== typeFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return e.employeeName.toLowerCase().includes(q) || e.description.toLowerCase().includes(q) || e.department.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Employee Lifecycle</h1>
        <p className="mt-1 text-sm text-gray-500">Track compliance across employee lifecycle events: onboarding, transfers, promotions, leaves, and exits</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "Events This Month", value: EVENTS.length, color: "text-blue-600" },
          { label: "Compliant", value: EVENTS.filter((e) => e.complianceStatus === "compliant").length, color: "text-green-600" },
          { label: "Warnings", value: EVENTS.filter((e) => e.complianceStatus === "warning").length, color: "text-yellow-600" },
          { label: "Violations", value: EVENTS.filter((e) => e.complianceStatus === "violation").length, color: "text-red-600" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{stat.label}</p>
            <p className={`mt-1 text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1">
          <label htmlFor="lifecycle-search" className="text-xs font-medium text-gray-500">Search</label>
          <input id="lifecycle-search" type="text" placeholder="Search by name, department, or description..." value={search} onChange={(e) => setSearch(e.target.value)} className="mt-0.5 block w-full rounded-lg border bg-white px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400" />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(Object.keys(EVENT_TYPE_LABELS) as EventType[]).map((t) => {
          const count = t === "all" ? EVENTS.length : EVENTS.filter((e) => e.eventType === t).length;
          return (
            <button key={t} type="button" onClick={() => setTypeFilter(t)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${typeFilter === t ? "border-indigo-400 bg-indigo-100 text-indigo-800" : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"}`}>
              {EVENT_TYPE_LABELS[t]} ({count})
            </button>
          );
        })}
      </div>

      {/* Event list */}
      <div className="overflow-x-auto rounded-xl border bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs uppercase text-gray-500">
              <th className="px-5 py-3">Event</th>
              <th className="px-5 py-3">Employee</th>
              <th className="px-5 py-3">Department</th>
              <th className="px-5 py-3">Date</th>
              <th className="px-5 py-3">Rules Checked</th>
              <th className="px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((event) => (
              <tr key={event.id} className="transition-colors hover:bg-gray-50">
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    <span>{EVENT_TYPE_ICON[event.eventType]}</span>
                    <div>
                      <p className="font-medium text-gray-900">{EVENT_TYPE_LABELS[event.eventType]}</p>
                      <p className="text-xs text-gray-500">{event.description}</p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <p className="font-medium text-gray-900">{event.employeeName}</p>
                  <p className="text-xs text-gray-400">{event.employeeId}</p>
                </td>
                <td className="px-5 py-3 text-gray-600">{event.department}</td>
                <td className="px-5 py-3 text-gray-600">{event.date}</td>
                <td className="px-5 py-3">
                  <span className="text-gray-600">{event.rulesChecked}</span>
                  {event.flaggedRules > 0 && <span className="ml-1 text-xs text-red-500">({event.flaggedRules} flagged)</span>}
                </td>
                <td className="px-5 py-3">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[event.complianceStatus]}`}>{event.complianceStatus}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="p-8 text-center text-sm text-gray-400">No lifecycle events match the selected filters.</div>
        )}
      </div>
    </div>
  );
}
