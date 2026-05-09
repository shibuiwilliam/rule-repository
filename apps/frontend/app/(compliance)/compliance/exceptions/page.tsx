"use client";

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

const EXCEPTIONS: ExceptionRecord[] = [
  { id: "EXC-001", ruleId: "R-OT-001", ruleStatement: "Monthly overtime MUST NOT exceed 45 hours", requester: "K. Watanabe", department: "Engineering", justification: "Critical production incident response — temporary 2-week exception", status: "approved", requestedAt: "2026-05-01", expiresAt: "2026-05-15" },
  { id: "EXC-002", ruleId: "R-LV-003", ruleStatement: "Leave requests MUST be submitted 14 days in advance", requester: "S. Kim", department: "Marketing", justification: "Family emergency — retroactive leave approval", status: "approved", requestedAt: "2026-05-05", expiresAt: "2026-05-06" },
  { id: "EXC-003", ruleId: "R-FIN-002", ruleStatement: "Expenses over JPY 100,000 require dual approval", requester: "M. Tanaka", department: "Finance", justification: "Urgent vendor payment — second approver on leave", status: "pending", requestedAt: "2026-05-08", expiresAt: "2026-05-10" },
  { id: "EXC-004", ruleId: "R-COM-005", ruleStatement: "External communications require comms department review", requester: "A. Suzuki", department: "Sales", justification: "Time-sensitive client response — post-hoc review requested", status: "denied", requestedAt: "2026-05-04", expiresAt: "2026-05-04" },
];

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  denied: "bg-red-100 text-red-800",
  expired: "bg-gray-100 text-gray-700",
};

export default function ExceptionsPage() {
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
            <p className={`mt-1 text-2xl font-bold ${STATUS_BADGE[s].split(" ")[1]}`}>{EXCEPTIONS.filter((e) => e.status === s).length}</p>
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
            {EXCEPTIONS.map((e) => (
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
