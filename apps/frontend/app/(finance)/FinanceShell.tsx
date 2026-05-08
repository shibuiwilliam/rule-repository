"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const FINANCE_NAV: NavItem[] = [
  { label: "Dashboard", href: "/finance", icon: "\ud83d\udcca" },
  { label: "Transactions", href: "/finance/transactions", icon: "\ud83d\udcb8" },
  { label: "Expense Policy", href: "/finance/expenses", icon: "\ud83e\uddfe" },
  { label: "Audit Reports", href: "/finance/audit", icon: "\ud83d\udccb" },
  { label: "Controls", href: "/finance/controls", icon: "\ud83d\udee1\ufe0f" },
];

export function FinanceShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Finance"
      personaIcon="\ud83d\udcb0"
      accentColor="bg-emerald-100 text-emerald-800"
      accentHover="hover:bg-emerald-100"
      navItems={FINANCE_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
