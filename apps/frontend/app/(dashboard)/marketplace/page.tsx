"use client";

import { useState, useEffect, useCallback } from "react";
import {
  type RulePackage,
  type PackageSubscription,
  getPackages,
  getSubscriptions,
  subscribeToPackage,
  unsubscribe,
} from "@/lib/api";
import { useProject } from "@/lib/project-context";

type TabKey = "all" | "published" | "subscriptions";

function qualityColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 50) return "text-yellow-600";
  return "text-red-600";
}

function qualityBg(score: number): string {
  if (score >= 80) return "bg-green-100 text-green-700";
  if (score >= 50) return "bg-yellow-100 text-yellow-700";
  return "bg-red-100 text-red-700";
}

export default function MarketplacePage() {
  const { currentProject } = useProject();
  const [tab, setTab] = useState<TabKey>("all");
  const [packages, setPackages] = useState<RulePackage[]>([]);
  const [subscriptions, setSubscriptions] = useState<PackageSubscription[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [subscribingId, setSubscribingId] = useState<string | null>(null);
  const [unsubscribingId, setUnsubscribingId] = useState<string | null>(null);

  const loadPackages = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getPackages(tab === "published", page, 20);
      setPackages(data.items);
      setTotal(data.total);
    } catch {
      setPackages([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [tab, page]);

  const loadSubscriptions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getSubscriptions(currentProject?.id);
      setSubscriptions(data.items);
      setTotal(data.total);
    } catch {
      setSubscriptions([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [currentProject?.id]);

  useEffect(() => {
    if (tab === "subscriptions") {
      loadSubscriptions();
    } else {
      loadPackages();
    }
  }, [tab, loadPackages, loadSubscriptions]);

  const handleSubscribe = async (pkg: RulePackage) => {
    if (!currentProject) return;
    setSubscribingId(pkg.id);
    try {
      await subscribeToPackage(currentProject.id, pkg.id);
      if (tab === "subscriptions") {
        await loadSubscriptions();
      }
    } catch {
      // error handled silently
    } finally {
      setSubscribingId(null);
    }
  };

  const handleUnsubscribe = async (subscriptionId: string) => {
    setUnsubscribingId(subscriptionId);
    try {
      await unsubscribe(subscriptionId);
      await loadSubscriptions();
    } catch {
      // error handled silently
    } finally {
      setUnsubscribingId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Rule Marketplace</h1>
        <p className="text-sm text-gray-500 mt-1">
          Browse, subscribe to, and share curated rule packages across projects.
        </p>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-2 border-b pb-2">
        {([
          { key: "all" as TabKey, label: "All Packages" },
          { key: "published" as TabKey, label: "Published" },
          { key: "subscriptions" as TabKey, label: "My Subscriptions" },
        ]).map((t) => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setPage(1); }}
            className={`px-3 py-1.5 text-sm rounded-t-md ${
              tab === t.key
                ? "bg-blue-50 text-blue-700 border-b-2 border-blue-600 font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : tab === "subscriptions" ? (
        /* Subscriptions list */
        subscriptions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg">No subscriptions yet</p>
            <p className="text-sm mt-1">
              Subscribe to published packages to sync rules into your project.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {subscriptions.map((sub: PackageSubscription) => (
              <div
                key={sub.id}
                className="border rounded-lg p-4 bg-white hover:border-blue-300 transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold">{sub.package_name}</h3>
                      <span className="text-xs text-gray-400 bg-gray-50 rounded px-1.5 py-0.5">
                        v{sub.installed_version}
                      </span>
                      {sub.auto_update && (
                        <span className="text-xs bg-blue-100 text-blue-700 rounded-full px-2 py-0.5">
                          auto-update
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      Constraint: {sub.version_constraint} -- Last synced:{" "}
                      {new Date(sub.last_synced_at).toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    onClick={() => handleUnsubscribe(sub.id)}
                    disabled={unsubscribingId === sub.id}
                    className="ml-4 shrink-0 rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                  >
                    {unsubscribingId === sub.id ? "Removing..." : "Unsubscribe"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        /* Package cards */
        packages.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg">No packages found</p>
            <p className="text-sm mt-1">
              {tab === "published"
                ? "No packages have been published yet."
                : "The marketplace is empty. Create your first rule package to get started."}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {packages.map((pkg: RulePackage) => (
              <div
                key={pkg.id}
                className="border rounded-lg p-4 bg-white hover:border-blue-300 transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold">{pkg.name}</h3>
                      <span className="text-xs text-gray-400 bg-gray-50 rounded px-1.5 py-0.5">
                        v{pkg.version}
                      </span>
                      {pkg.published ? (
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700">
                          published
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700">
                          draft
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-600 mt-1">
                      {pkg.description || "No description"}
                    </p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      <span>Publisher: {pkg.publisher_id}</span>
                      <span>License: {pkg.license}</span>
                      <span>{pkg.rule_count} rule(s)</span>
                      <span>{pkg.adoption_count} subscriber(s)</span>
                      {pkg.published_at && (
                        <span>Published {new Date(pkg.published_at).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 ml-4 shrink-0">
                    <div className="text-center">
                      <span className={`text-lg font-bold ${qualityColor(pkg.quality_score)}`}>
                        {pkg.quality_score}
                      </span>
                      <p className="text-[10px] text-gray-400 leading-tight">quality</p>
                    </div>
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${qualityBg(pkg.quality_score)}`}
                    >
                      {pkg.quality_score >= 80
                        ? "High"
                        : pkg.quality_score >= 50
                          ? "Medium"
                          : "Low"}
                    </span>
                    {pkg.published && currentProject && (
                      <button
                        onClick={() => handleSubscribe(pkg)}
                        disabled={subscribingId === pkg.id}
                        className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        {subscribingId === pkg.id ? "Subscribing..." : "Subscribe"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* Pagination (not shown for subscriptions tab) */}
      {tab !== "subscriptions" && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded border px-3 py-1 text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded border px-3 py-1 text-sm disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
