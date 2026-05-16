"use client";

export default function BillingPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Billing & Usage</h1>
        <p className="mt-1 text-sm text-gray-500">LLM token usage, cost tracking, and tenant budgets</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border bg-white p-5 text-center">
          <p className="text-xs font-semibold uppercase text-gray-400">This Month</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">¥12,340</p>
          <p className="mt-1 text-sm text-gray-500">LLM cost</p>
        </div>
        <div className="rounded-xl border bg-white p-5 text-center">
          <p className="text-xs font-semibold uppercase text-gray-400">Evaluations</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">1,847</p>
          <p className="mt-1 text-sm text-gray-500">this month</p>
        </div>
        <div className="rounded-xl border bg-white p-5 text-center">
          <p className="text-xs font-semibold uppercase text-gray-400">Budget Used</p>
          <p className="mt-2 text-3xl font-bold text-yellow-600">62%</p>
          <p className="mt-1 text-sm text-gray-500">of monthly cap</p>
        </div>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Cost Guardrails</h2>
        <p className="mt-2 text-sm text-gray-500">
          Per-tenant monthly budgets with 80% warning and 100% hard cap.
          Configure via <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">LLM_TENANT_OVERRIDES</code> environment variable.
        </p>
      </div>
    </div>
  );
}
