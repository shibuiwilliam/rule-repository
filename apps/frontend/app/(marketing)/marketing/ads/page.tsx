"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface AdComplianceCheckpoint {
  id: number;
  regulation: string;
  description: string;
  severity: string;
  checks: string[];
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
};

export default function AdCompliancePage() {
  const [checkpoints, setCheckpoints] = useState<AdComplianceCheckpoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ ad_compliance_checkpoints: AdComplianceCheckpoint[] }>("marketing").then((d) => {
      setCheckpoints(d.ad_compliance_checkpoints ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Ad Compliance</h1>
        <p className="mt-1 text-sm text-gray-500">
          Advertising regulation rules and compliance checkpoints applicable to marketing
          creatives, campaigns, and communications
        </p>
      </div>

      <div className="rounded-xl border bg-blue-50 p-4 text-sm text-blue-800">
        All advertising materials must be reviewed against applicable regulations before
        publication. Critical violations may result in regulatory action, fines, or mandatory
        corrective advertising.
      </div>

      <div className="space-y-4">
        {checkpoints.map((cp) => (
          <div key={cp.id} className="rounded-xl border bg-white p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-semibold text-gray-900">{cp.regulation}</h2>
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[cp.severity] ?? "bg-gray-100 text-gray-700"}`}
                  >
                    {cp.severity}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-600">{cp.description}</p>
              </div>
            </div>
            <ul className="mt-3 space-y-1">
              {cp.checks.map((check, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-0.5 text-gray-400">&#x2022;</span>
                  {check}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
