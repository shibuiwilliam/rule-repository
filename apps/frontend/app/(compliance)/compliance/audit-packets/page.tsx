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

const PACKETS: AuditPacket[] = [
  { id: "AP-2026-Q1", title: "Q1 2026 Compliance Audit — HR", scope: "hr/attendance, hr/overtime", period: "2026-01 to 2026-03", status: "finalized", rulesIncluded: 25, evaluationsIncluded: 342, createdAt: "2026-04-05", reviewer: "M. Tanaka" },
  { id: "AP-2026-Q1-FIN", title: "Q1 2026 Compliance Audit — Finance", scope: "finance/expense, finance/tax", period: "2026-01 to 2026-03", status: "in_review", rulesIncluded: 18, evaluationsIncluded: 156, createdAt: "2026-04-10", reviewer: "K. Sato" },
  { id: "AP-2026-Q1-LEGAL", title: "Q1 2026 Contract Review Audit", scope: "legal/contract", period: "2026-01 to 2026-03", status: "in_review", rulesIncluded: 30, evaluationsIncluded: 47, createdAt: "2026-04-12", reviewer: "T. Yamada" },
  { id: "AP-2026-Q2-HR", title: "Q2 2026 Compliance Audit — HR (Draft)", scope: "hr/attendance, hr/overtime, hr/leave", period: "2026-04 to 2026-06", status: "draft", rulesIncluded: 25, evaluationsIncluded: 0, createdAt: "2026-05-01", reviewer: "" },
];

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  in_review: "bg-yellow-100 text-yellow-800",
  finalized: "bg-green-100 text-green-800",
};

export default function AuditPacketsPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Packets</h1>
        <p className="mt-1 text-sm text-gray-500">Bundled compliance evidence packets for internal and external audits</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { label: "Finalized", value: PACKETS.filter((p) => p.status === "finalized").length, color: "text-green-600" },
          { label: "In Review", value: PACKETS.filter((p) => p.status === "in_review").length, color: "text-yellow-600" },
          { label: "Drafts", value: PACKETS.filter((p) => p.status === "draft").length, color: "text-gray-600" },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>
      <div className="space-y-3">
        {PACKETS.map((p) => (
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
