"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

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
  const [events, setEvents] = useState<LifecycleEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState<EventType>("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchSeedData<{ lifecycle_events: LifecycleEvent[] }>("hr").then((d) => {
      setEvents(d.lifecycle_events ?? []);
      setLoading(false);
    });
  }, []);

  const filtered = events.filter((e) => {
    if (typeFilter !== "all" && e.eventType !== typeFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return e.employeeName.toLowerCase().includes(q) || e.description.toLowerCase().includes(q) || e.department.toLowerCase().includes(q);
    }
    return true;
  });

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Employee Lifecycle</h1>
        <p className="mt-1 text-sm text-gray-500">Track compliance across employee lifecycle events: onboarding, transfers, promotions, leaves, and exits</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "Events This Month", value: events.length, color: "text-blue-600" },
          { label: "Compliant", value: events.filter((e) => e.complianceStatus === "compliant").length, color: "text-green-600" },
          { label: "Warnings", value: events.filter((e) => e.complianceStatus === "warning").length, color: "text-yellow-600" },
          { label: "Violations", value: events.filter((e) => e.complianceStatus === "violation").length, color: "text-red-600" },
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
          const count = t === "all" ? events.length : events.filter((e) => e.eventType === t).length;
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
