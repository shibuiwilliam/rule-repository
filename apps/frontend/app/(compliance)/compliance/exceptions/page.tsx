"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface ExceptionRecord {
  id: string;
  ruleId: string;
  ruleStatement: string;
  requester: string;
  department: string;
  justification: string;
  status: "pending" | "approved" | "denied" | "expired";
  requestedAt: string;
  expiresAt: string;
}

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  denied: "bg-red-100 text-red-800",
  expired: "bg-gray-100 text-gray-700",
};

export default function ExceptionsPage() {
  const [exceptions, setExceptions] = useState<ExceptionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ exceptions: ExceptionRecord[] }>("compliance").then((d) => {
      setExceptions(d.exceptions ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Exception Tracking</h1>
        <p className="mt-1 text-sm text-gray-500">Track one-time rule exceptions, approvals, and their expiry across all domains</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {(["pending", "approved", "denied", "expired"] as const).map((s) => (
          <div key={s} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{s.charAt(0).toUpperCase() + s.slice(1)}</p>
            <p className={`mt-1 text-2xl font-bold ${STATUS_BADGE[s].split(" ")[1]}`}>{exceptions.filter((e) => e.status === s).length}</p>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-xl border bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs uppercase text-gray-500">
              <th className="px-5 py-3">Rule</th>
              <th className="px-5 py-3">Requester</th>
              <th className="px-5 py-3">Justification</th>
              <th className="px-5 py-3">Requested</th>
              <th className="px-5 py-3">Expires</th>
              <th className="px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {exceptions.map((e) => (
              <tr key={e.id} className="hover:bg-gray-50">
                <td className="px-5 py-3">
                  <p className="text-sm text-gray-900">{e.ruleStatement}</p>
                  <p className="text-xs text-gray-400">{e.ruleId}</p>
                </td>
                <td className="px-5 py-3 text-gray-600">{e.requester}<br /><span className="text-xs text-gray-400">{e.department}</span></td>
                <td className="max-w-xs px-5 py-3 text-xs text-gray-600">{e.justification}</td>
                <td className="px-5 py-3 text-gray-600">{e.requestedAt}</td>
                <td className="px-5 py-3 text-gray-600">{e.expiresAt}</td>
                <td className="px-5 py-3"><span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[e.status]}`}>{e.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
