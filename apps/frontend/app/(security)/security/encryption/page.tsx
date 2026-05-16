"use client";

export default function EncryptionPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Encryption & Key Management</h1>
        <p className="mt-1 text-sm text-gray-500">
          Customer-managed encryption keys (CMEK) and data-at-rest status
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border bg-green-50 p-5 text-center">
          <p className="text-3xl font-bold text-green-700">AES-256</p>
          <p className="mt-1 text-sm text-green-600">At-rest encryption</p>
        </div>
        <div className="rounded-xl border bg-green-50 p-5 text-center">
          <p className="text-3xl font-bold text-green-700">TLS 1.3</p>
          <p className="mt-1 text-sm text-green-600">In-transit encryption</p>
        </div>
        <div className="rounded-xl border bg-gray-50 p-5 text-center">
          <p className="text-3xl font-bold text-gray-500">—</p>
          <p className="mt-1 text-sm text-gray-500">CMEK not configured</p>
        </div>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">CMEK Configuration</h2>
        <p className="mt-2 text-sm text-gray-500">
          Customer-managed encryption keys allow tenants to control the encryption keys
          used for their data at rest. Configure via environment variables{" "}
          <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">AUDIT_WORM_S3_BUCKET</code> and{" "}
          <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">AUDIT_WORM_S3_REGION</code>.
        </p>
      </div>
    </div>
  );
}
