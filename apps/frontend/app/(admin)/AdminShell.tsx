"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const ADMIN_NAV: NavItem[] = [
  { label: "Dashboard", href: "/admin", icon: "\ud83d\udcca" },
  { label: "Tenants", href: "/admin/tenants", icon: "\ud83c\udfe2" },
  { label: "Users", href: "/admin/users", icon: "\ud83d\udc64" },
  { label: "Connectors", href: "/admin/connectors", icon: "\ud83d\udd0c" },
  { label: "Settings", href: "/admin/settings", icon: "\u2699\ufe0f" },
  { label: "Billing", href: "/admin/billing", icon: "\ud83d\udcb3" },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Admin"
      personaIcon="\ud83d\udd27"
      accentColor="bg-gray-200 text-gray-800"
      accentHover="hover:bg-gray-200"
      navItems={ADMIN_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
