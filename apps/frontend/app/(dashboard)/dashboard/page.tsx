"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

import { usePersona, type Persona } from "../PersonaSwitcher";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface SummaryData {
  total_rules: number;
  compliance_rate: number;
  evaluations_today: number;
  pending_actions: number;
  rules_by_status: Record<string, number>;
  top_violated_rules: Array<{ rule_id: string; statement: string; deny_count: number }>;
}

function useSummary() {
  const [data, setData] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/intelligence/summary`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);
  return { data, loading };
}

function KpiCard({ label, value, color = "text-gray-900" }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="rounded-lg border bg-white p-6">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function QuickLinks({ links }: { links: Array<{ href: string; label: string; desc: string }> }) {
  return (
    <div className="mt-8">
      <h2 className="mb-4 text-lg font-semibold">Quick Actions</h2>
      <div className="grid grid-cols-2 gap-3">
        {links.map((l) => (
          <Link key={l.href} href={l.href} className="rounded-lg border p-4 hover:border-blue-300 hover:bg-blue-50">
            <p className="text-sm font-medium">{l.label}</p>
            <p className="mt-1 text-xs text-gray-500">{l.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ---- Per-persona dashboard layouts ----

function ComplianceDashboard({ data }: { data: SummaryData | null }) {
  const rate = data ? Math.round((data.compliance_rate ?? 0) * 100) : 0;
  return (
    <div>
      <h1 className="text-2xl font-bold">Compliance Dashboard</h1>
      <p className="mt-1 text-sm text-gray-500">Regulatory progress, audit readiness, and alerts</p>
      <div className="mt-6 grid grid-cols-4 gap-4">
        <KpiCard label="Compliance Rate" value={`${rate}%`} color={rate >= 90 ? "text-green-600" : rate >= 70 ? "text-yellow-600" : "text-red-600"} />
        <KpiCard label="Active Rules" value={data?.total_rules ?? 0} />
        <KpiCard label="Evaluations Today" value={data?.evaluations_today ?? 0} />
        <KpiCard label="Pending Actions" value={data?.pending_actions ?? 0} />
      </div>
      <QuickLinks links={[
        { href: "/audit", label: "Audit Log", desc: "View hash-chained audit trail" },
        { href: "/rules", label: "Rule Library", desc: "Browse all compliance rules" },
        { href: "/proposals", label: "Pending Proposals", desc: "Review rule change requests" },
        { href: "/intelligence", label: "Analytics", desc: "Compliance trends and metrics" },
      ]} />
    </div>
  );
}

function LegalDashboard({ data }: { data: SummaryData | null }) {
  return (
    <div>
      <h1 className="text-2xl font-bold">Legal Counsel Dashboard</h1>
      <p className="mt-1 text-sm text-gray-500">Contract review, NDA compliance, and regulatory tracking</p>
      <div className="mt-6 grid grid-cols-3 gap-4">
        <KpiCard label="Active Rules" value={data?.total_rules ?? 0} />
        <KpiCard label="Pending Reviews" value={data?.pending_actions ?? 0} />
        <KpiCard label="Evaluations Today" value={data?.evaluations_today ?? 0} />
      </div>
      <QuickLinks links={[
        { href: "/rules?scope=legal", label: "Contract Rules", desc: "NDA, MSA, and procurement rules" },
        { href: "/documents", label: "Document Review", desc: "Upload contracts for clause analysis" },
        { href: "/proposals", label: "Rule Proposals", desc: "Review and approve rule changes" },
        { href: "/audit", label: "Audit Reports", desc: "Export compliance evidence" },
      ]} />
    </div>
  );
}

function HrDashboard({ data }: { data: SummaryData | null }) {
  return (
    <div>
      <h1 className="text-2xl font-bold">HR Manager Dashboard</h1>
      <p className="mt-1 text-sm text-gray-500">Attendance compliance, leave management, and labor law adherence</p>
      <div className="mt-6 grid grid-cols-3 gap-4">
        <KpiCard label="Active HR Rules" value={data?.total_rules ?? 0} />
        <KpiCard label="Evaluations Today" value={data?.evaluations_today ?? 0} />
        <KpiCard label="Pending Actions" value={data?.pending_actions ?? 0} />
      </div>
      <QuickLinks links={[
        { href: "/rules?scope=hr", label: "HR Rules", desc: "Attendance, overtime, and leave rules" },
        { href: "/discover", label: "Discover Rules", desc: "Extract rules from work regulations" },
        { href: "/playground", label: "Test Scenarios", desc: "Test HR events against rules" },
        { href: "/intelligence", label: "Compliance Trends", desc: "Track HR compliance metrics" },
      ]} />
    </div>
  );
}

function FinanceDashboard({ data }: { data: SummaryData | null }) {
  return (
    <div>
      <h1 className="text-2xl font-bold">Finance Controller Dashboard</h1>
      <p className="mt-1 text-sm text-gray-500">Expense compliance, invoice validation, and financial controls</p>
      <div className="mt-6 grid grid-cols-3 gap-4">
        <KpiCard label="Active Rules" value={data?.total_rules ?? 0} />
        <KpiCard label="Evaluations Today" value={data?.evaluations_today ?? 0} />
        <KpiCard label="Pending Actions" value={data?.pending_actions ?? 0} />
      </div>
      <QuickLinks links={[
        { href: "/rules?scope=finance", label: "Finance Rules", desc: "Expense, invoice, and revenue rules" },
        { href: "/gateway", label: "Expense Gateway", desc: "Configure auto-evaluation of expense claims" },
        { href: "/audit", label: "Audit Reports", desc: "J-SOX and financial audit evidence" },
        { href: "/intelligence", label: "Cost Analytics", desc: "Evaluation costs and trends" },
      ]} />
    </div>
  );
}

function EngineeringDashboard({ data }: { data: SummaryData | null }) {
  const rate = data ? Math.round((data.compliance_rate ?? 0) * 100) : 0;
  return (
    <div>
      <h1 className="text-2xl font-bold">Engineering Dashboard</h1>
      <p className="mt-1 text-sm text-gray-500">Code compliance, agent governance, and engineering standards</p>
      <div className="mt-6 grid grid-cols-4 gap-4">
        <KpiCard label="Compliance Rate" value={`${rate}%`} color={rate >= 90 ? "text-green-600" : "text-yellow-600"} />
        <KpiCard label="Active Rules" value={data?.total_rules ?? 0} />
        <KpiCard label="Evaluations Today" value={data?.evaluations_today ?? 0} />
        <KpiCard label="Pending Actions" value={data?.pending_actions ?? 0} />
      </div>
      {data?.top_violated_rules && data.top_violated_rules.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-3 text-lg font-semibold">Top Violated Rules</h2>
          <div className="space-y-2">
            {data.top_violated_rules.slice(0, 5).map((r) => (
              <div key={r.rule_id} className="rounded border p-3 text-sm">
                <span className="font-medium">{r.statement.slice(0, 80)}</span>
                <span className="ml-2 text-red-600">({r.deny_count} violations)</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <QuickLinks links={[
        { href: "/rules?scope=engineering", label: "Engineering Rules", desc: "Python, API, security, testing rules" },
        { href: "/agents", label: "Agent Governance", desc: "AI agent compliance and trust levels" },
        { href: "/integrations", label: "CI/CD Integration", desc: "GitHub, hooks, and pipelines" },
        { href: "/feedback", label: "Correction Flywheel", desc: "Review human corrections" },
      ]} />
    </div>
  );
}

function ExecutiveDashboard({ data }: { data: SummaryData | null }) {
  const rate = data ? Math.round((data.compliance_rate ?? 0) * 100) : 0;
  return (
    <div>
      <h1 className="text-2xl font-bold">Executive Overview</h1>
      <p className="mt-1 text-sm text-gray-500">Organization-wide compliance posture and risk indicators</p>
      <div className="mt-6 grid grid-cols-4 gap-4">
        <KpiCard label="Overall Compliance" value={`${rate}%`} color={rate >= 90 ? "text-green-600" : rate >= 70 ? "text-yellow-600" : "text-red-600"} />
        <KpiCard label="Total Rules" value={data?.total_rules ?? 0} />
        <KpiCard label="Daily Evaluations" value={data?.evaluations_today ?? 0} />
        <KpiCard label="Action Items" value={data?.pending_actions ?? 0} />
      </div>
      {data?.rules_by_status && (
        <div className="mt-8">
          <h2 className="mb-3 text-lg font-semibold">Rules by Status</h2>
          <div className="grid grid-cols-5 gap-3">
            {Object.entries(data.rules_by_status).map(([status, count]) => (
              <div key={status} className="rounded border p-3 text-center">
                <p className="text-xs text-gray-500">{status}</p>
                <p className="text-lg font-bold">{count}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      <QuickLinks links={[
        { href: "/intelligence", label: "Full Analytics", desc: "Deep dive into compliance metrics" },
        { href: "/audit", label: "Audit Reports", desc: "Framework-specific compliance evidence" },
      ]} />
    </div>
  );
}

function DefaultDashboard({ data }: { data: SummaryData | null }) {
  const rate = data ? Math.round((data.compliance_rate ?? 0) * 100) : 0;
  return (
    <div>
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="mt-1 text-sm text-gray-500">Select a persona to see a tailored view</p>
      <div className="mt-6 grid grid-cols-4 gap-4">
        <KpiCard label="Compliance Rate" value={`${rate}%`} />
        <KpiCard label="Active Rules" value={data?.total_rules ?? 0} />
        <KpiCard label="Evaluations Today" value={data?.evaluations_today ?? 0} />
        <KpiCard label="Pending Actions" value={data?.pending_actions ?? 0} />
      </div>
    </div>
  );
}

// ---- Main dashboard page ----

const PERSONA_DASHBOARDS: Record<Persona, React.FC<{ data: SummaryData | null }>> = {
  all: DefaultDashboard,
  compliance: ComplianceDashboard,
  legal: LegalDashboard,
  hr: HrDashboard,
  finance: FinanceDashboard,
  engineering: EngineeringDashboard,
  sales: DefaultDashboard,
  executive: ExecutiveDashboard,
};

export default function PersonaDashboardPage() {
  const { persona } = usePersona();
  const { data, loading } = useSummary();
  const Dashboard = PERSONA_DASHBOARDS[persona] ?? DefaultDashboard;

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-lg bg-gray-100" />
        ))}
      </div>
    );
  }

  return <Dashboard data={data} />;
}
