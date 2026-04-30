import Link from "next/link";
import type { HomeSummary, ComplianceTrendPoint } from "@/lib/api";

const API_BASE =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";

async function getSummary(): Promise<HomeSummary | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/intelligence/summary`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json() as Promise<HomeSummary>;
  } catch {
    return null;
  }
}

async function getHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/healthz`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

/* ---------- Sub-components ---------- */

function ComplianceHero({
  rate,
  trend,
}: {
  rate: number;
  trend: HomeSummary["compliance_trend"];
}) {
  const pct = Math.round(rate * 100);
  const color =
    pct >= 90
      ? "text-green-600"
      : pct >= 70
        ? "text-yellow-600"
        : "text-red-600";
  const bg =
    pct >= 90
      ? "bg-green-50 border-green-200"
      : pct >= 70
        ? "bg-yellow-50 border-yellow-200"
        : "bg-red-50 border-red-200";

  return (
    <div className={`rounded-xl border-2 p-6 ${bg}`}>
      <p className="text-sm font-medium uppercase tracking-wider text-gray-500">
        Agent Compliance Rate (30d)
      </p>
      <div className="mt-2 flex items-end gap-6">
        <span className={`text-5xl font-bold ${color}`}>{pct}%</span>
        {trend.length > 1 && (
          <div className="flex items-end gap-0.5 pb-2">
            {trend.map((point: ComplianceTrendPoint, i: number) => {
              const h = Math.max(4, Math.round(point.compliance_rate * 40));
              return (
                <div
                  key={i}
                  className="w-5 rounded-t bg-blue-400"
                  style={{ height: `${h}px` }}
                  title={`${point.date}: ${Math.round(point.compliance_rate * 100)}%`}
                />
              );
            })}
          </div>
        )}
      </div>
      {trend.length > 1 && (
        <p className="mt-2 text-xs text-gray-400">
          7-day trend ({trend.length} days with evaluations)
        </p>
      )}
    </div>
  );
}

function RulesStatusBar({
  total,
  byStatus,
}: {
  total: number;
  byStatus: Record<string, number>;
}) {
  const statuses = [
    { key: "EFFECTIVE", label: "Effective", color: "bg-green-500" },
    { key: "APPROVED", label: "Approved", color: "bg-blue-500" },
    { key: "DRAFT", label: "Draft", color: "bg-yellow-400" },
    { key: "REVIEW", label: "Review", color: "bg-orange-400" },
    { key: "RETIRED", label: "Retired", color: "bg-gray-400" },
  ];

  return (
    <div className="rounded-lg border bg-white p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium uppercase tracking-wider text-gray-500">
          Rules
        </p>
        <span className="text-2xl font-bold text-gray-800">{total}</span>
      </div>
      {total > 0 && (
        <>
          <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-gray-100">
            {statuses.map(({ key, color }) => {
              const count = byStatus[key] ?? 0;
              if (count === 0) return null;
              const pct = (count / total) * 100;
              return (
                <div
                  key={key}
                  className={`${color}`}
                  style={{ width: `${pct}%` }}
                  title={`${key}: ${count}`}
                />
              );
            })}
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
            {statuses.map(({ key, label, color }) => {
              const count = byStatus[key] ?? 0;
              if (count === 0) return null;
              return (
                <span key={key} className="flex items-center gap-1">
                  <span className={`inline-block h-2 w-2 rounded-full ${color}`} />
                  {label}: {count}
                </span>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

function PendingActions({
  actions,
}: {
  actions: HomeSummary["pending_actions"];
}) {
  const items = [
    {
      label: "Rules Pending Review",
      count: actions.rules_pending_review,
      href: "/rules",
      color: "text-orange-600 bg-orange-50 border-orange-200",
    },
    {
      label: "Corrections Pending",
      count: actions.corrections_pending,
      href: "/feedback",
      color: "text-blue-600 bg-blue-50 border-blue-200",
    },
    {
      label: "Active Alerts",
      count: actions.active_alerts,
      href: "/alerts",
      color: "text-red-600 bg-red-50 border-red-200",
    },
  ];

  return (
    <div className="rounded-lg border bg-white p-5">
      <p className="mb-3 text-sm font-medium uppercase tracking-wider text-gray-500">
        Pending Actions
      </p>
      <div className="flex gap-3">
        {items.map((item) => (
          <Link
            key={item.label}
            href={item.href}
            className={`flex flex-1 flex-col items-center rounded-lg border p-3 transition-colors hover:opacity-80 ${item.color}`}
          >
            <span className="text-2xl font-bold">{item.count}</span>
            <span className="mt-1 text-center text-xs">{item.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

function TopViolatedRules({
  rules,
}: {
  rules: HomeSummary["top_violated_rules"];
}) {
  if (rules.length === 0) {
    return (
      <div className="rounded-lg border bg-white p-5">
        <p className="text-sm font-medium uppercase tracking-wider text-gray-500">
          Top Violated Rules
        </p>
        <p className="mt-3 text-sm text-gray-400">No violations recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-white p-5">
      <p className="mb-3 text-sm font-medium uppercase tracking-wider text-gray-500">
        Top Violated Rules (30d)
      </p>
      <div className="space-y-2">
        {rules.map((item: HomeSummary["top_violated_rules"][number]) => (
          <div
            key={item.rule_id}
            className="flex items-center justify-between rounded-md border px-3 py-2"
          >
            <div className="min-w-0 flex-1">
              <Link
                href={`/rules/${item.rule_id}`}
                className="text-sm text-blue-600 hover:underline"
              >
                {item.rule_statement
                  ? item.rule_statement.length > 80
                    ? `${item.rule_statement.slice(0, 80)}...`
                    : item.rule_statement
                  : `Rule ${item.rule_id.slice(0, 8)}...`}
              </Link>
            </div>
            <span className="ml-3 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700">
              {item.violation_count} deny
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecentCorrections({
  corrections,
}: {
  corrections: HomeSummary["recent_corrections"];
}) {
  const statusColors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    approved: "bg-green-100 text-green-800",
    dismissed: "bg-gray-100 text-gray-600",
  };

  if (corrections.length === 0) {
    return (
      <div className="rounded-lg border bg-white p-5">
        <p className="text-sm font-medium uppercase tracking-wider text-gray-500">
          Recent Corrections
        </p>
        <p className="mt-3 text-sm text-gray-400">No corrections submitted yet.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-white p-5">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-medium uppercase tracking-wider text-gray-500">
          Recent Corrections
        </p>
        <Link
          href="/feedback"
          className="text-xs text-blue-600 hover:underline"
        >
          View all
        </Link>
      </div>
      <div className="space-y-2">
        {corrections.map((c: HomeSummary["recent_corrections"][number]) => (
          <div
            key={c.id}
            className="flex items-center justify-between rounded-md border px-3 py-2"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm">
                {c.candidate_statement || c.analysis_type || "Correction"}
              </p>
              <p className="text-xs text-gray-400">
                {new Date(c.created_at).toLocaleDateString()}
              </p>
            </div>
            <span
              className={`ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[c.status] ?? "bg-gray-100"}`}
            >
              {c.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- Main Page ---------- */

export default async function HomePage() {
  const [summary, healthy] = await Promise.all([getSummary(), getHealth()]);

  // Graceful degradation: if API is unreachable, show minimal page
  if (!summary) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight">Rule Repository</h1>
          <p className="mt-3 text-lg text-gray-600">
            Manage, search, and enforce natural-language rules
          </p>
        </div>
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <span
              className={`inline-block h-3 w-3 rounded-full ${healthy ? "bg-green-500" : "bg-red-500"}`}
            />
            <span className="text-lg font-semibold">
              {healthy ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>
        <nav className="flex gap-4">
          <Link
            href="/rules"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Browse Rules
          </Link>
          <Link
            href="/search"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-100"
          >
            Search
          </Link>
          <Link
            href="/documents"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-100"
          >
            Documents
          </Link>
        </nav>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 p-6 lg:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Rule Repository
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              Governance dashboard — are your rules working?
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
            <span className="text-sm text-gray-500">Connected</span>
          </div>
        </div>

        {/* Hero: Compliance Rate */}
        <ComplianceHero
          rate={summary.compliance_rate}
          trend={summary.compliance_trend}
        />

        {/* Rules + Pending Actions */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <RulesStatusBar
            total={summary.total_rules}
            byStatus={summary.rules_by_status}
          />
          <PendingActions actions={summary.pending_actions} />
        </div>

        {/* Violated Rules + Recent Corrections */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <TopViolatedRules rules={summary.top_violated_rules} />
          <RecentCorrections corrections={summary.recent_corrections} />
        </div>

        {/* Quick Nav */}
        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            href="/rules"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Browse Rules
          </Link>
          <Link
            href="/search"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-100"
          >
            Search
          </Link>
          <Link
            href="/documents"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-100"
          >
            Documents
          </Link>
          <Link
            href="/playground"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-100"
          >
            Playground
          </Link>
          <Link
            href="/intelligence"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-100"
          >
            Intelligence
          </Link>
        </div>
      </div>
    </main>
  );
}
