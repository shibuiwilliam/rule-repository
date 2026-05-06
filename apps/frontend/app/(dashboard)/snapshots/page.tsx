"use client";

import { useState, useEffect, useCallback } from "react";
import {
  type Snapshot,
  type Deployment,
  type SimulateResult,
  createSnapshot,
  getSnapshots,
  deploySnapshot,
  rollbackSnapshot,
  simulateSnapshot,
  getDeployments,
} from "@/lib/api";
import { useProject } from "@/lib/project-context";

type DeployEnv = "production" | "staging" | "development";

export default function SnapshotsPage() {
  const { currentProject } = useProject();
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Create form
  const [name, setName] = useState("");
  const [scopeFilter, setScopeFilter] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  // Simulation
  const [simResult, setSimResult] = useState<SimulateResult | null>(null);
  const [simulating, setSimulating] = useState<string | null>(null);

  // Deploy dropdown
  const [deployDropdown, setDeployDropdown] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [snaps, deps] = await Promise.all([getSnapshots(currentProject?.id), getDeployments()]);
      setSnapshots(snaps);
      setDeployments(deps);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [currentProject?.id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleCreate = async () => {
    if (!name.trim()) {
      setError("Snapshot name is required.");
      return;
    }
    setError("");
    setMessage("");
    setCreating(true);
    try {
      const scopes = scopeFilter
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await createSnapshot({
        name,
        scope_filter: scopes.length > 0 ? scopes : undefined,
        description: description || undefined,
        project_id: currentProject?.id,
      });
      setName("");
      setScopeFilter("");
      setDescription("");
      setMessage("Snapshot created successfully.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create snapshot");
    } finally {
      setCreating(false);
    }
  };

  const handleDeploy = async (snapshotId: string, env: DeployEnv) => {
    setError("");
    setMessage("");
    setDeployDropdown(null);
    try {
      await deploySnapshot(snapshotId, env);
      setMessage(`Deployed to ${env} successfully.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deploy failed");
    }
  };

  const handleRollback = async (snapshotId: string) => {
    setError("");
    setMessage("");
    try {
      await rollbackSnapshot(snapshotId);
      setMessage("Rollback completed.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rollback failed");
    }
  };

  const handleSimulate = async (snapshotId: string) => {
    setError("");
    setSimResult(null);
    setSimulating(snapshotId);
    try {
      const res = await simulateSnapshot(snapshotId);
      setSimResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setSimulating(null);
    }
  };

  const isDeployed = (snapshotId: string) =>
    deployments.some((d) => d.snapshot_id === snapshotId && d.active);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-500">
        Loading snapshots...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold" title="Create versioned snapshots of rule sets for deployment to environments">Rule Set Snapshots</h1>
        <p className="mt-1 text-sm text-gray-500">
          Version, deploy, and roll back rule sets
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {message && (
        <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {message}
        </div>
      )}

      {/* Create snapshot form */}
      <div className="rounded-lg border bg-white p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">
          Create Snapshot
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label htmlFor="snap-name" className="mb-1 block text-sm font-medium text-gray-700">
              Name
            </label>
            <input
              id="snap-name"
              type="text"
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="e.g. v2.3-release"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="snap-scope" className="mb-1 block text-sm font-medium text-gray-700">
              Scope Filter (comma-separated)
            </label>
            <input
              id="snap-scope"
              type="text"
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="e.g. security, compliance"
              value={scopeFilter}
              onChange={(e) => setScopeFilter(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="snap-desc" className="mb-1 block text-sm font-medium text-gray-700">
              Description
            </label>
            <textarea
              id="snap-desc"
              rows={1}
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Optional description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>
        <div className="mt-4">
          <button
            onClick={handleCreate}
            disabled={creating}
            className="rounded-md bg-blue-600 px-5 py-2 text-sm font-semibold text-white shadow hover:bg-blue-700 disabled:opacity-50"
            title="Capture the current rule set as a named, immutable snapshot"
          >
            {creating ? "Creating..." : "Create Snapshot"}
          </button>
        </div>
      </div>

      {/* Snapshots table */}
      <div className="rounded-lg border bg-white">
        <div className="border-b px-5 py-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Snapshots
          </h2>
        </div>
        {snapshots.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-gray-400">No snapshots yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-5 py-3">Name</th>
                  <th className="px-5 py-3">Rules</th>
                  <th className="px-5 py-3">Scope</th>
                  <th className="px-5 py-3">Created</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {snapshots.map((snap) => (
                  <tr key={snap.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-medium">{snap.name}</td>
                    <td className="px-5 py-3">{snap.rule_count}</td>
                    <td className="px-5 py-3">
                      {snap.scope_filter.length > 0
                        ? snap.scope_filter.join(", ")
                        : <span className="text-gray-400">all</span>}
                    </td>
                    <td className="px-5 py-3 text-gray-500">
                      {new Date(snap.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3">
                      {isDeployed(snap.id) ? (
                        <span className="inline-block rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                          Deployed
                        </span>
                      ) : (
                        <span className="inline-block rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                          Available
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        {/* Deploy dropdown */}
                        <div className="relative">
                          <button
                            onClick={() =>
                              setDeployDropdown(deployDropdown === snap.id ? null : snap.id)
                            }
                            className="rounded border px-3 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50"
                            title="Deploy this snapshot to an environment"
                          >
                            Deploy
                          </button>
                          {deployDropdown === snap.id && (
                            <div className="absolute left-0 z-10 mt-1 w-36 rounded-md border bg-white shadow-lg">
                              {(["production", "staging", "development"] as DeployEnv[]).map(
                                (env) => (
                                  <button
                                    key={env}
                                    onClick={() => handleDeploy(snap.id, env)}
                                    className="block w-full px-4 py-2 text-left text-xs hover:bg-gray-100"
                                  >
                                    {env}
                                  </button>
                                ),
                              )}
                            </div>
                          )}
                        </div>

                        <button
                          onClick={() => handleSimulate(snap.id)}
                          disabled={simulating === snap.id}
                          className="rounded border px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                          title="Preview the impact of deploying this snapshot"
                        >
                          {simulating === snap.id ? "Simulating..." : "Simulate"}
                        </button>

                        {isDeployed(snap.id) && (
                          <button
                            onClick={() => handleRollback(snap.id)}
                            className="rounded border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                            title="Revert the active deployment to this snapshot"
                          >
                            Rollback
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Simulation result */}
      {simResult && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-blue-800">
            Simulation Result
          </h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <p className="text-xs text-blue-600">Total Replayed</p>
              <p className="text-lg font-semibold text-blue-900">{simResult.total_replayed}</p>
            </div>
            <div>
              <p className="text-xs text-blue-600">Rules Added</p>
              <p className="text-lg font-semibold text-green-700">+{simResult.rules_added}</p>
            </div>
            <div>
              <p className="text-xs text-blue-600">Rules Removed</p>
              <p className="text-lg font-semibold text-red-700">-{simResult.rules_removed}</p>
            </div>
            <div>
              <p className="text-xs text-blue-600">Risk Assessment</p>
              <p className="text-sm font-medium text-blue-900">{simResult.risk_assessment}</p>
            </div>
          </div>
        </div>
      )}

      {/* Active deployments */}
      {deployments.filter((d) => d.active).length > 0 && (
        <div className="rounded-lg border bg-white">
          <div className="border-b px-5 py-3">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
              Active Deployments
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-5 py-3">Environment</th>
                  <th className="px-5 py-3">Snapshot</th>
                  <th className="px-5 py-3">Deployed At</th>
                  <th className="px-5 py-3">Deployed By</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {deployments
                  .filter((d) => d.active)
                  .map((dep) => {
                    const snap = snapshots.find((s) => s.id === dep.snapshot_id);
                    return (
                      <tr key={dep.id} className="hover:bg-gray-50">
                        <td className="px-5 py-3">
                          <span className="inline-block rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                            {dep.environment}
                          </span>
                        </td>
                        <td className="px-5 py-3 font-medium">{snap?.name ?? dep.snapshot_id}</td>
                        <td className="px-5 py-3 text-gray-500">
                          {new Date(dep.deployed_at).toLocaleString()}
                        </td>
                        <td className="px-5 py-3 text-gray-500">{dep.deployed_by}</td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
