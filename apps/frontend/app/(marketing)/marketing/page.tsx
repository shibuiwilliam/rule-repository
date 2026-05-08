import Link from "next/link";

export default function MarketingDashboardPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Marketing Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Creative compliance, ad review, and brand rule management</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Pending Creative Reviews</p>
          <p className="mt-1 text-3xl font-bold text-yellow-600">6</p>
          <p className="mt-1 text-xs text-gray-400">3 high priority</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Ad Compliance Rate</p>
          <p className="mt-1 text-3xl font-bold text-green-600">92%</p>
          <p className="mt-1 text-xs text-gray-400">Last 30 days</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Brand Rule Violations</p>
          <p className="mt-1 text-3xl font-bold text-red-600">3</p>
          <p className="mt-1 text-xs text-gray-400">Keihyohou / Yakkihou</p>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-sm font-medium text-gray-500">Active Marketing Rules</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">18</p>
          <p className="mt-1 text-xs text-gray-400">2 under review</p>
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Recent Creative Reviews</h2>
        </div>
        <div className="divide-y">
          {[
            { id: "CR-201", title: "Q2 Product Launch Banner", type: "Display Ad", status: "pending", issues: 2 },
            { id: "CR-202", title: "Email Campaign - Summer Sale", type: "Email", status: "approved", issues: 0 },
            { id: "CR-203", title: "Social Media Ad - Health Supplement", type: "Social Ad", status: "denied", issues: 3 },
            { id: "CR-204", title: "Landing Page - New Feature", type: "Web Page", status: "pending", issues: 1 },
          ].map((cr) => (
            <div key={cr.id} className="flex items-center gap-4 px-5 py-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">{cr.title}</p>
                <p className="text-xs text-gray-500">{cr.type} | {cr.issues} issue{cr.issues !== 1 ? "s" : ""}</p>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                cr.status === "approved" ? "bg-green-100 text-green-700" : cr.status === "denied" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
              }`}>{cr.status}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link href="/marketing/creatives" className="rounded-xl border bg-white p-4 transition-colors hover:border-purple-300 hover:bg-purple-50">
          <p className="text-sm font-medium text-gray-900">Creative Review</p>
          <p className="mt-1 text-xs text-gray-500">Submit and review marketing creatives</p>
        </Link>
        <Link href="/marketing/ads" className="rounded-xl border bg-white p-4 transition-colors hover:border-purple-300 hover:bg-purple-50">
          <p className="text-sm font-medium text-gray-900">Ad Compliance</p>
          <p className="mt-1 text-xs text-gray-500">Keihyohou and Yakkihou compliance checks</p>
        </Link>
        <Link href="/marketing/brand" className="rounded-xl border bg-white p-4 transition-colors hover:border-purple-300 hover:bg-purple-50">
          <p className="text-sm font-medium text-gray-900">Brand Rules</p>
          <p className="mt-1 text-xs text-gray-500">Brand guidelines and usage standards</p>
        </Link>
      </div>
    </div>
  );
}
