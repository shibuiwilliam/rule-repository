"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const SALES_NAV: NavItem[] = [
  { label: "Dashboard", href: "/sales", icon: "📊" },
  { label: "Pricing Approvals", href: "/sales/pricing", icon: "🏷️" },
  { label: "Discount Requests", href: "/sales/discounts", icon: "💸" },
  { label: "Proposals", href: "/sales/proposals", icon: "📄" },
  { label: "Communication", href: "/sales/communication", icon: "📧" },
];

export function SalesShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Sales"
      personaIcon="📈"
      accentColor="bg-orange-100 text-orange-800"
      accentHover="hover:bg-orange-100"
      navItems={SALES_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
