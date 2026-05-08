"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const COMPLIANCE_NAV: NavItem[] = [
  { label: "Dashboard", href: "/compliance", icon: "\ud83d\udcca" },
  { label: "Bundles", href: "/compliance/bundles", icon: "\ud83d\udce6" },
  { label: "Audit Packets", href: "/compliance/audit-packets", icon: "\ud83d\udcce" },
  { label: "Exception Tracking", href: "/compliance/exceptions", icon: "\u26a0\ufe0f" },
  { label: "Regulatory Feed", href: "/compliance/regulatory", icon: "\ud83d\udce1" },
];

export function ComplianceShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Compliance"
      personaIcon="\ud83d\udee1\ufe0f"
      accentColor="bg-amber-100 text-amber-800"
      accentHover="hover:bg-amber-100"
      navItems={COMPLIANCE_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
