"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const LEGAL_NAV: NavItem[] = [
  { label: "Dashboard", href: "/legal", icon: "📊" },
  { label: "Contract Review", href: "/legal/contracts", icon: "📝" },
  { label: "Clause Library", href: "/legal/clauses", icon: "📚" },
  { label: "Redlines", href: "/legal/redlines", icon: "🗒️" },
  { label: "Norm Lineage", href: "/legal/lineage", icon: "🗂️" },
  { label: "Regulatory Horizon", href: "/legal/regulatory", icon: "🌐" },
  { label: "Citations", href: "/legal/citations", icon: "🔗" },
];

export function LegalShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Legal"
      personaIcon="⚖️"
      accentColor="bg-slate-200 text-slate-800"
      accentHover="hover:bg-slate-200"
      navItems={LEGAL_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
