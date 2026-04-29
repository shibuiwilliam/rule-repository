"use client";

import { useState } from "react";
import { useProject } from "@/lib/project-context";

export default function ProjectsPage() {
  const { projects, currentProject, selectProject, createAndSelect, refresh, loading } =
    useProject();

  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    if (!name.trim()) {
      setError("Project name is required.");
      return;
    }
    setError("");
    setCreating(true);
    try {
      await createAndSelect(name.trim(), description.trim() || undefined);
      setName("");
      setDescription("");
      setShowCreate(false);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage projects to organize rules, documents, and other resources
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {showCreate ? "Cancel" : "New Project"}
        </button>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="rounded-lg border bg-white p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">
            Create Project
          </h2>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Web Coding Rules"
                className="w-full max-w-md rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Description <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this project for?"
                className="w-full max-w-md rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <button
              onClick={handleCreate}
              disabled={creating}
              className="rounded-md bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create Project"}
            </button>
          </div>
        </div>
      )}

      {/* Project list */}
      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg border bg-gray-100" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-white p-8 text-center">
          <p className="text-sm text-gray-500">
            No projects yet. Create one to get started.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {projects.map((p) => (
            <div
              key={p.id}
              className={`flex items-center justify-between rounded-lg border bg-white p-4 ${
                currentProject?.id === p.id ? "border-blue-500 ring-1 ring-blue-200" : ""
              }`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold">{p.name}</h3>
                  {currentProject?.id === p.id && (
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                      active
                    </span>
                  )}
                </div>
                {p.description && (
                  <p className="mt-0.5 text-xs text-gray-500">{p.description}</p>
                )}
                <p className="mt-1 font-mono text-xs text-gray-400">{p.id}</p>
              </div>
              {currentProject?.id !== p.id && (
                <button
                  onClick={() => selectProject(p.id)}
                  className="rounded border px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
                >
                  Switch to this project
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
