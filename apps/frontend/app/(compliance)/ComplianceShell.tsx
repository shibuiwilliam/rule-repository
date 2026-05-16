"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const COMPLIANCE_NAV: NavItem[] = [
  { label: "Dashboard", href: "/compliance", icon: "📊" },
  { label: "Bundles", href: "/compliance/bundles", icon: "📦" },
  { label: "Audit Packets", href: "/compliance/audit-packets", icon: "📎" },
  { label: "Exception Tracking", href: "/compliance/exceptions", icon: "⚠️" },
  { label: "Regulatory Feed", href: "/compliance/regulatory", icon: "📡" },
];

export function ComplianceShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Compliance"
      personaIcon="🛡️"
      accentColor="bg-amber-100 text-amber-800"
      accentHover="hover:bg-amber-100"
      navItems={COMPLIANCE_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
