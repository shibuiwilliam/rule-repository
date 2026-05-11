"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const SALES_NAV: NavItem[] = [
  { label: "Dashboard", href: "/sales", icon: "\ud83d\udcca" },
  { label: "Pricing Approvals", href: "/sales/pricing", icon: "\ud83c\udff7\ufe0f" },
  { label: "Discount Requests", href: "/sales/discounts", icon: "\ud83d\udcb8" },
  { label: "Proposals", href: "/sales/proposals", icon: "\ud83d\udcc4" },
  { label: "Communication", href: "/sales/communication", icon: "\ud83d\udce7" },
];

export function SalesShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Sales"
      personaIcon="&#x1F4C8;"
      accentColor="bg-orange-100 text-orange-800"
      accentHover="hover:bg-orange-100"
      navItems={SALES_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
