"use client";

export default function CitationsPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Citations</h1>
        <p className="mt-1 text-sm text-gray-500">
          Source references and regulatory citations linked to rules
        </p>
      </div>

      <div className="rounded-xl border bg-white p-6">
        <p className="text-sm text-gray-500">
          Citations track the provenance of each rule back to its source
          document, statute, or regulatory authority. Use the search below
          to find rules by citation.
        </p>

        <div className="mt-6 space-y-4">
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
            <p className="text-sm text-gray-600">
              No citations indexed yet. Citations are populated when rules
              are extracted from source documents via the extraction pipeline,
              or when manually linked through the rule editor.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
