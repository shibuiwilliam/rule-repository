"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface AuditPacket {
  id: string;
  title: string;
  scope: string;
  period: string;
  status: "draft" | "in_review" | "finalized";
  rulesIncluded: number;
  evaluationsIncluded: number;
  createdAt: string;
  reviewer: string;
}

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  in_review: "bg-yellow-100 text-yellow-800",
  finalized: "bg-green-100 text-green-800",
};

export default function AuditPacketsPage() {
  const [packets, setPackets] = useState<AuditPacket[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ audit_packets: AuditPacket[] }>("compliance").then((d) => {
      setPackets(d.audit_packets ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Packets</h1>
        <p className="mt-1 text-sm text-gray-500">Bundled compliance evidence packets for internal and external audits</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { label: "Finalized", value: packets.filter((p) => p.status === "finalized").length, color: "text-green-600" },
          { label: "In Review", value: packets.filter((p) => p.status === "in_review").length, color: "text-yellow-600" },
          { label: "Drafts", value: packets.filter((p) => p.status === "draft").length, color: "text-gray-600" },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>
      <div className="space-y-3">
        {packets.map((p) => (
          <div key={p.id} className="rounded-xl border bg-white p-5 hover:border-amber-300 transition-colors">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-gray-900">{p.title}</h3>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[p.status]}`}>{p.status.replace("_", " ")}</span>
                </div>
                <p className="mt-1 text-xs text-gray-500">{p.scope} | {p.period}</p>
                <div className="mt-2 flex gap-4 text-xs text-gray-400">
                  <span>{p.rulesIncluded} rules</span>
                  <span>{p.evaluationsIncluded} evaluations</span>
                  <span>Created {p.createdAt}</span>
                  {p.reviewer && <span>Reviewer: {p.reviewer}</span>}
                </div>
              </div>
              <span className="text-xs text-gray-400">{p.id}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
