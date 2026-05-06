import Link from "next/link";

import { ProjectProvider } from "@/lib/project-context";
import { ProjectSelector } from "./ProjectSelector";

const NAV_ITEMS = [
  { href: "/rules", label: "Rules", section: "manage", tooltip: "Browse, create, and manage natural-language rules with conditions, examples, and relationships" },
  { href: "/proposals", label: "Proposals", section: "manage", tooltip: "Propose rule changes through a collaborative workflow with multi-approver voting and impact analysis" },
  { href: "/search", label: "Search", section: "manage", tooltip: "Search rules and documents using full-text, semantic, or hybrid search across all projects" },
  { href: "/documents", label: "Documents", section: "manage", tooltip: "Upload documents (PDF, text, markdown) and extract rules using the LLM-powered extraction pipeline" },
  { href: "/discover", label: "Discover", section: "manage", tooltip: "Discover implicit rules from CLAUDE.md files, linter configs, code patterns, and policy documents" },
  { href: "/federations", label: "Federations", section: "manage", tooltip: "Organize rules into org/team/project hierarchy with inheritance and overrides" },
  { href: "/playground", label: "Playground", section: "manage", tooltip: "Test rules in a sandbox with code or scenario inputs, generate test cases, and validate rule behavior" },
  { href: "/snapshots", label: "Snapshots", section: "manage", tooltip: "Create versioned snapshots of rule sets, deploy to environments, simulate impact, and rollback" },
  { href: "/intelligence", label: "Intelligence", section: "observe", tooltip: "Monitor rule health scores, analytics, compliance trends, cache performance, and AI-generated recommendations" },
  { href: "/feedback", label: "Feedback", section: "observe", tooltip: "Review human corrections of AI-generated code, approve rule proposals from the self-improving flywheel" },
  { href: "/notifications", label: "Notifications", section: "observe", tooltip: "View notifications for proposal activity, approval requests, and governance events" },
  { href: "/agents", label: "Agents", section: "observe", tooltip: "Track AI agent compliance leaderboard, trust levels, rule mastery, and verdict challenges" },
  { href: "/review", label: "Review", section: "enforce", tooltip: "Run two-tier compliance reviews: rough triage across all rules, then detailed LLM evaluation" },
  { href: "/gateway", label: "Gateway", section: "enforce", tooltip: "Configure webhook-driven enforcement policies that automatically evaluate incoming events" },
  { href: "/integrations", label: "Integrations", section: "enforce", tooltip: "Set up GitHub App for PR review, CI pipeline checks, and agent hook integration" },
  { href: "/marketplace", label: "Marketplace", section: "share", tooltip: "Browse, publish, and subscribe to versioned rule packages shared across teams" },
  { href: "/projects", label: "Projects", section: "settings", tooltip: "Create and manage projects that scope rules, documents, evaluations, and all other resources" },
];

const SECTION_TOOLTIPS: Record<string, string> = {
  manage: "Create, organize, and test your rules",
  observe: "Monitor compliance, health, and agent behavior",
  enforce: "Automatically evaluate and enforce rules",
  share: "Distribute rule packages across teams",
  settings: "Configure projects and preferences",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <div className="flex min-h-screen">
        {/* Sidebar */}
        <aside className="w-64 border-r bg-white px-4 py-6">
          <Link href="/" className="mb-4 block text-xl font-bold tracking-tight" title="Home dashboard with compliance rate, trends, and pending actions">
            Rule Repository
          </Link>

          {/* Project selector */}
          <ProjectSelector />

          <nav className="mt-6 space-y-6">
            {["manage", "observe", "enforce", "share", "settings"].map((section) => (
              <div key={section}>
                <p
                  className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-gray-400"
                  title={SECTION_TOOLTIPS[section]}
                >
                  {section}
                </p>
                {NAV_ITEMS.filter((i) => i.section === section).map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
                    title={item.tooltip}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            ))}
          </nav>
        </aside>

        {/* Main content */}
        <main className="flex-1 bg-gray-50 p-8">{children}</main>
      </div>
    </ProjectProvider>
  );
}
