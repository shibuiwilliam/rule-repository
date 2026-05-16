"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const ADMIN_NAV: NavItem[] = [
  { label: "Dashboard", href: "/admin", icon: "📊" },
  { label: "Tenants", href: "/admin/tenants", icon: "🏢" },
  { label: "Users", href: "/admin/users", icon: "👤" },
  { label: "Settings", href: "/admin/settings", icon: "⚙️" },
  { label: "Billing", href: "/admin/billing", icon: "💳" },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Admin"
      personaIcon="🔧"
      accentColor="bg-gray-200 text-gray-800"
      accentHover="hover:bg-gray-200"
      navItems={ADMIN_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
