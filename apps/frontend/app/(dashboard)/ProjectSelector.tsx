"use client";

import { useProject } from "@/lib/project-context";

export function ProjectSelector() {
  const { currentProject, projects, selectProject, loading } = useProject();

  if (loading) {
    return (
      <div className="rounded-md border bg-gray-50 px-3 py-2">
        <p className="text-xs text-gray-400">Loading projects...</p>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="rounded-md border border-dashed bg-gray-50 px-3 py-2">
        <p className="text-xs text-gray-400">No projects yet</p>
      </div>
    );
  }

  return (
    <div>
      <label htmlFor="project-select" className="mb-1 block px-1 text-xs font-semibold uppercase tracking-wider text-gray-400">
        Project
      </label>
      <select
        id="project-select"
        value={currentProject?.id ?? ""}
        onChange={(e) => selectProject(e.target.value)}
        className="w-full rounded-md border bg-white px-3 py-2 text-sm font-medium text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
    </div>
  );
}
