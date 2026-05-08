"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const LEGAL_NAV: NavItem[] = [
  { label: "Dashboard", href: "/legal", icon: "\ud83d\udcca" },
  { label: "Contract Review", href: "/legal/contracts", icon: "\ud83d\udcdd" },
  { label: "Clause Library", href: "/legal/clauses", icon: "\ud83d\udcda" },
  { label: "Regulatory Horizon", href: "/legal/regulatory", icon: "\ud83c\udf10" },
  { label: "Citations", href: "/legal/citations", icon: "\ud83d\udd17" },
];

export function LegalShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Legal"
      personaIcon="\u2696\ufe0f"
      accentColor="bg-slate-200 text-slate-800"
      accentHover="hover:bg-slate-200"
      navItems={LEGAL_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
