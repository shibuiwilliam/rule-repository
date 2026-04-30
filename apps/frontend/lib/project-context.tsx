"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { type Project, getProjects, createProject as apiCreateProject } from "./api";

interface ProjectContextValue {
  /** Currently selected project, or null if none selected. */
  currentProject: Project | null;
  /** All available projects. */
  projects: Project[];
  /** Select a project by ID. */
  selectProject: (id: string) => void;
  /** Create a new project and select it. */
  createAndSelect: (name: string, description?: string) => Promise<Project>;
  /** Refresh the project list from the server. */
  refresh: () => Promise<void>;
  /** True while loading projects. */
  loading: boolean;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

const STORAGE_KEY = "rulerepo_current_project_id";

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  const loadProjects = useCallback(async () => {
    try {
      const data = await getProjects(1, 200);
      setProjects(data.items);
      return data.items;
    } catch {
      return [];
    }
  }, []);

  // Initial load
  useEffect(() => {
    (async () => {
      setLoading(true);
      const items = await loadProjects();
      // Restore selection from localStorage
      const savedId =
        typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
      const saved = savedId ? items.find((p) => p.id === savedId) : null;
      setCurrentProject(saved ?? items[0] ?? null);
      setLoading(false);
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const selectProject = useCallback(
    (id: string) => {
      const project = projects.find((p) => p.id === id) ?? null;
      setCurrentProject(project);
      if (project) {
        localStorage.setItem(STORAGE_KEY, project.id);
      }
    },
    [projects],
  );

  const createAndSelect = useCallback(
    async (name: string, description?: string): Promise<Project> => {
      const created = await apiCreateProject({ name, description });
      setProjects((prev) => [...prev, created]);
      setCurrentProject(created);
      localStorage.setItem(STORAGE_KEY, created.id);
      return created;
    },
    [],
  );

  const refresh = useCallback(async () => {
    const items = await loadProjects();
    // Keep current selection if still valid
    if (currentProject && !items.find((p) => p.id === currentProject.id)) {
      setCurrentProject(items[0] ?? null);
    }
  }, [loadProjects, currentProject]);

  return (
    <ProjectContext.Provider
      value={{ currentProject, projects, selectProject, createAndSelect, refresh, loading }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) {
    throw new Error("useProject must be used within a ProjectProvider");
  }
  return ctx;
}
