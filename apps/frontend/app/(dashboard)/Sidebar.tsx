"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import { usePersona, PERSONA_SECTIONS, PersonaSwitcher } from "./PersonaSwitcher";
import { PersonaSwitcher as PortalSwitcher } from "@/components/PersonaSwitcher";
import { ProjectSelector } from "./ProjectSelector";

const GATEWAY_ENABLED = process.env.NEXT_PUBLIC_GATEWAY_ENABLED === "true";

const NAV_ITEMS = [
  // Observe
  { href: "/dashboard", key: "dashboard", section: "observe" },
  { href: "/intelligence", key: "intelligence", section: "observe" },
  { href: "/compliance", key: "compliance", section: "observe" },
  { href: "/feedback", key: "feedback", section: "observe" },
  { href: "/notifications", key: "notifications", section: "observe" },
  { href: "/agents", key: "agents", section: "observe" },
  { href: "/audit", key: "audit", section: "observe" },
  // Manage
  { href: "/rules", key: "rules", section: "manage" },
  { href: "/discover", key: "discover", section: "manage" },
  { href: "/documents", key: "documents", section: "manage" },
  { href: "/proposals", key: "proposals", section: "manage" },
  { href: "/snapshots", key: "snapshots", section: "manage" },
  { href: "/departments", key: "departments", section: "manage" },
  // Use
  { href: "/assistant", key: "assistant", section: "use" },
  { href: "/ask", key: "ask", section: "use" },
  { href: "/search", key: "search", section: "use" },
  { href: "/playground", key: "playground", section: "use" },
  // Enforce
  { href: "/review", key: "review", section: "enforce" },
  ...(GATEWAY_ENABLED ? [{ href: "/gateway", key: "gateway", section: "enforce" }] : []),
  { href: "/federations", key: "federations", section: "enforce" },
  // Settings
  { href: "/projects", key: "projects", section: "settings" },
  { href: "/onboarding", key: "onboarding", section: "settings" },
  { href: "/integrations", key: "integrations", section: "settings" },
];

export function Sidebar() {
  const { persona } = usePersona();
  const visibleSections = PERSONA_SECTIONS[persona];
  const tNav = useTranslations("nav");
  const tPages = useTranslations("pages");
  const tApp = useTranslations("app");

  return (
    <aside className="flex w-64 flex-col border-r bg-white px-4 py-6">
      <Link href="/" className="mb-4 block text-xl font-bold tracking-tight">
        {tApp("title")}
      </Link>

      {/* Portal switcher — navigate to other department portals */}
      <div className="mb-3">
        <PortalSwitcher />
      </div>

      <ProjectSelector />
      <PersonaSwitcher />

      <nav className="mt-6 flex-1 space-y-6 overflow-y-auto">
        {visibleSections.map((section) => (
          <div key={section}>
            <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
              {tNav(section)}
            </p>
            {NAV_ITEMS.filter((i) => i.section === section).map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
              >
                {tPages(item.key)}
              </Link>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
