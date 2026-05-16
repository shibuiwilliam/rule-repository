"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const SECURITY_NAV: NavItem[] = [
  { label: "Dashboard", href: "/security", icon: "📊" },
  { label: "Classification", href: "/security/classification", icon: "🏷️" },
  { label: "Encryption", href: "/security/encryption", icon: "🔐" },
  { label: "Eval Harness", href: "/security/eval-harness", icon: "🧪" },
  { label: "Access Logs", href: "/security/access-logs", icon: "📝" },
];

export function SecurityShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Security"
      personaIcon="🔒"
      accentColor="bg-red-100 text-red-800"
      accentHover="hover:bg-red-100"
      navItems={SECURITY_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
