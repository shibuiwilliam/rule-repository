"use client";

export default function RegulatoryHorizonPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Regulatory Horizon</h1>
        <p className="mt-1 text-sm text-gray-500">
          Track upcoming regulatory changes and their impact on internal rules
        </p>
      </div>

      <div className="rounded-xl border bg-white p-6">
        <p className="text-sm text-gray-500">
          The regulatory horizon scanner monitors source regulations for amendments
          and uses the provenance lineage graph to identify all downstream internal
          rules that may need review.
        </p>

        <div className="mt-6 space-y-4">
          <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
            <p className="text-sm font-medium text-blue-900">No pending regulatory changes</p>
            <p className="mt-1 text-xs text-blue-700">
              When source regulations are amended, affected rules will appear here
              with impact analysis and suggested revision plans.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
