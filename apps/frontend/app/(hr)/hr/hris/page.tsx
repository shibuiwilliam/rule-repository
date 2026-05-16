"use client";

export default function HrisStatusPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">HRIS Integration Status</h1>
        <p className="mt-1 text-sm text-gray-500">
          Connection status and sync health for HR information systems
        </p>
      </div>

      <div className="rounded-xl border bg-white p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="flex items-center gap-3">
              <span className="flex h-3 w-3 rounded-full bg-green-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">Rule Repository API</p>
                <p className="text-xs text-gray-500">Core evaluation engine</p>
              </div>
            </div>
            <span className="text-xs font-medium text-green-700">Connected</span>
          </div>

          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="flex items-center gap-3">
              <span className="flex h-3 w-3 rounded-full bg-gray-300" />
              <div>
                <p className="text-sm font-medium text-gray-900">HR System (HRIS)</p>
                <p className="text-xs text-gray-500">Employee data, attendance, leave records</p>
              </div>
            </div>
            <span className="text-xs font-medium text-gray-500">Not configured</span>
          </div>

          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="flex items-center gap-3">
              <span className="flex h-3 w-3 rounded-full bg-gray-300" />
              <div>
                <p className="text-sm font-medium text-gray-900">Payroll System</p>
                <p className="text-xs text-gray-500">Overtime hours, compensation data</p>
              </div>
            </div>
            <span className="text-xs font-medium text-gray-500">Not configured</span>
          </div>
        </div>

        <p className="mt-6 text-sm text-gray-500">
          Configure HRIS integrations to enable automatic event submission via{" "}
          <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">POST /api/v1/submissions</code>{" "}
          for real-time compliance checking of HR events.
        </p>
      </div>
    </div>
  );
}
