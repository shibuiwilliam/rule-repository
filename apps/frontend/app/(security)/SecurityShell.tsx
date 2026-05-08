"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const SECURITY_NAV: NavItem[] = [
  { label: "Dashboard", href: "/security", icon: "\ud83d\udcca" },
  { label: "Classification", href: "/security/classification", icon: "\ud83c\udff7\ufe0f" },
  { label: "Encryption", href: "/security/encryption", icon: "\ud83d\udd10" },
  { label: "Eval Harness", href: "/security/eval-harness", icon: "\ud83e\uddea" },
  { label: "Access Logs", href: "/security/access-logs", icon: "\ud83d\udcdd" },
];

export function SecurityShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Security"
      personaIcon="\ud83d\udd12"
      accentColor="bg-red-100 text-red-800"
      accentHover="hover:bg-red-100"
      navItems={SECURITY_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
