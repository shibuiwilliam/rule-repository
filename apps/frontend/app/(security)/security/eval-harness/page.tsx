"use client";

const DOMAINS = [
  { name: "Engineering", cases: 15, lastRun: "2026-05-14", pass: 14, fail: 1 },
  { name: "Legal", cases: 12, lastRun: "2026-05-14", pass: 11, fail: 1 },
  { name: "HR", cases: 10, lastRun: "2026-05-14", pass: 10, fail: 0 },
  { name: "Finance", cases: 12, lastRun: "2026-05-14", pass: 12, fail: 0 },
  { name: "IT Security", cases: 10, lastRun: "2026-05-14", pass: 9, fail: 1 },
  { name: "Sales", cases: 8, lastRun: "2026-05-14", pass: 8, fail: 0 },
  { name: "Communications", cases: 10, lastRun: "2026-05-14", pass: 10, fail: 0 },
  { name: "Governance", cases: 13, lastRun: "2026-05-14", pass: 12, fail: 1 },
];

export default function EvalHarnessPage() {
  const total = DOMAINS.reduce((s, d) => s + d.cases, 0);
  const passed = DOMAINS.reduce((s, d) => s + d.pass, 0);

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Eval Harness</h1>
        <p className="mt-1 text-sm text-gray-500">
          Golden-dataset evaluation results across all domains
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border bg-white p-5 text-center">
          <p className="text-3xl font-bold text-gray-900">{total}</p>
          <p className="mt-1 text-sm text-gray-500">Total cases</p>
        </div>
        <div className="rounded-xl border bg-green-50 p-5 text-center">
          <p className="text-3xl font-bold text-green-700">{passed}</p>
          <p className="mt-1 text-sm text-green-600">Passed</p>
        </div>
        <div className="rounded-xl border bg-red-50 p-5 text-center">
          <p className="text-3xl font-bold text-red-700">{total - passed}</p>
          <p className="mt-1 text-sm text-red-600">Failed</p>
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-gray-50">
            <tr>
              <th className="px-5 py-3 font-medium text-gray-600">Domain</th>
              <th className="px-5 py-3 font-medium text-gray-600">Cases</th>
              <th className="px-5 py-3 font-medium text-gray-600">Pass</th>
              <th className="px-5 py-3 font-medium text-gray-600">Fail</th>
              <th className="px-5 py-3 font-medium text-gray-600">Last Run</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {DOMAINS.map((d) => (
              <tr key={d.name}>
                <td className="px-5 py-3 font-medium text-gray-900">{d.name}</td>
                <td className="px-5 py-3">{d.cases}</td>
                <td className="px-5 py-3 text-green-700">{d.pass}</td>
                <td className="px-5 py-3 text-red-700">{d.fail || "—"}</td>
                <td className="px-5 py-3 text-gray-500">{d.lastRun}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
