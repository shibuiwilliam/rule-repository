"use client";

const LEVELS = [
  { level: "PUBLIC", color: "bg-green-100 text-green-700 border-green-200", description: "No restrictions — visible to all users and external parties", ruleCount: 42 },
  { level: "INTERNAL", color: "bg-blue-100 text-blue-700 border-blue-200", description: "Visible to authenticated users within the organization", ruleCount: 185 },
  { level: "CONFIDENTIAL", color: "bg-yellow-100 text-yellow-700 border-yellow-200", description: "Restricted access — evaluation logs masked on frontend", ruleCount: 67 },
  { level: "RESTRICTED", color: "bg-red-100 text-red-700 border-red-200", description: "Self-hosted LLM only — logs purge after 90 days", ruleCount: 23 },
];

export default function ClassificationPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Classification</h1>
        <p className="mt-1 text-sm text-gray-500">
          Classification levels and their enforcement policies
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {LEVELS.map((l) => (
          <div key={l.level} className={`rounded-xl border p-5 ${l.color}`}>
            <h3 className="text-lg font-bold">{l.level}</h3>
            <p className="mt-1 text-sm opacity-80">{l.description}</p>
            <p className="mt-3 text-2xl font-bold">{l.ruleCount}</p>
            <p className="text-xs opacity-70">rules at this level</p>
          </div>
        ))}
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Enforcement Policy</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="px-4 py-2 font-medium text-gray-600">Level</th>
                <th className="px-4 py-2 font-medium text-gray-600">LLM Routing</th>
                <th className="px-4 py-2 font-medium text-gray-600">Log Retention</th>
                <th className="px-4 py-2 font-medium text-gray-600">Frontend Masking</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr><td className="px-4 py-2 font-medium">PUBLIC</td><td className="px-4 py-2">Any provider</td><td className="px-4 py-2">Standard</td><td className="px-4 py-2">None</td></tr>
              <tr><td className="px-4 py-2 font-medium">INTERNAL</td><td className="px-4 py-2">Any provider</td><td className="px-4 py-2">Standard</td><td className="px-4 py-2">None</td></tr>
              <tr><td className="px-4 py-2 font-medium">CONFIDENTIAL</td><td className="px-4 py-2">Primary provider</td><td className="px-4 py-2">Standard</td><td className="px-4 py-2">Logs masked</td></tr>
              <tr><td className="px-4 py-2 font-medium">RESTRICTED</td><td className="px-4 py-2">Self-hosted only</td><td className="px-4 py-2">90-day purge</td><td className="px-4 py-2">Logs masked</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
