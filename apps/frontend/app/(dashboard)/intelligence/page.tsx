const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface DashboardData {
  total_rules: number;
  avg_health_score: number;
  total_evaluations_30d: number;
  verdict_distribution: Record<string, number>;
  active_drift_alerts: number;
  open_recommendations: number;
  health_distribution: Record<string, number>;
}

interface HealthScore {
  rule_id: string;
  overall_score: number;
  completeness: number;
  clarity: number;
  freshness: number;
  activity: number;
  issues: string[];
}

interface Recommendation {
  id: string;
  rule_id: string;
  type: string;
  title: string;
  description: string;
  priority: string;
}

async function fetchDashboard(): Promise<DashboardData | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/intelligence/dashboard`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function fetchHealthScores(): Promise<{ items: HealthScore[] } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/intelligence/health?page_size=20`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function fetchRecommendations(): Promise<{ items: Recommendation[] } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/intelligence/recommendations?page_size=10`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function healthColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  if (score >= 40) return "text-orange-500";
  return "text-red-600";
}

const PRIORITY_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-600",
};

export default async function IntelligencePage() {
  const [dashboard, health, recs] = await Promise.all([
    fetchDashboard(),
    fetchHealthScores(),
    fetchRecommendations(),
  ]);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Intelligence Dashboard</h1>

      {/* Summary cards */}
      {dashboard && (
        <div className="grid grid-cols-4 gap-4">
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Total Rules</p>
            <p className="text-3xl font-bold">{dashboard.total_rules}</p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Avg Health Score</p>
            <p className={`text-3xl font-bold ${healthColor(dashboard.avg_health_score)}`}>
              {dashboard.avg_health_score}
            </p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Evaluations (30d)</p>
            <p className="text-3xl font-bold">{dashboard.total_evaluations_30d}</p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Open Recommendations</p>
            <p className="text-3xl font-bold">{dashboard.open_recommendations}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Health scores table */}
        <div className="rounded-lg border bg-white p-4">
          <h2 className="mb-3 text-sm font-medium uppercase text-gray-500">Rule Health Scores</h2>
          {!health || health.items.length === 0 ? (
            <p className="text-sm text-gray-500">No rules to analyze yet.</p>
          ) : (
            <div className="space-y-2">
              {health.items.map((h) => (
                <div key={h.rule_id} className="flex items-center justify-between text-sm">
                  <a
                    href={`/rules/${h.rule_id}`}
                    className="font-mono text-xs text-blue-600 hover:underline"
                  >
                    {h.rule_id.slice(0, 8)}...
                  </a>
                  <div className="flex gap-3">
                    <span className={`font-bold ${healthColor(h.overall_score)}`}>
                      {h.overall_score.toFixed(0)}
                    </span>
                    <span className="text-gray-400" title="Completeness">
                      C:{h.completeness.toFixed(0)}
                    </span>
                    <span className="text-gray-400" title="Freshness">
                      F:{h.freshness.toFixed(0)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recommendations */}
        <div className="rounded-lg border bg-white p-4">
          <h2 className="mb-3 text-sm font-medium uppercase text-gray-500">Recommendations</h2>
          {!recs || recs.items.length === 0 ? (
            <p className="text-sm text-gray-500">No recommendations at this time.</p>
          ) : (
            <div className="space-y-3">
              {recs.items.map((r) => (
                <div key={r.id} className="border-l-2 border-gray-200 pl-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_STYLES[r.priority] ?? "bg-gray-100"}`}
                    >
                      {r.priority}
                    </span>
                    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                      {r.type}
                    </span>
                  </div>
                  <p className="mt-1 text-sm font-medium">{r.title}</p>
                  <p className="text-xs text-gray-500">{r.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
