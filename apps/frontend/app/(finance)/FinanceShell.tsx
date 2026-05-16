"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const FINANCE_NAV: NavItem[] = [
  { label: "Dashboard", href: "/finance", icon: "📊" },
  { label: "Transactions", href: "/finance/transactions", icon: "💸" },
  { label: "Expense Policy", href: "/finance/expenses", icon: "🧾" },
  { label: "Audit Reports", href: "/finance/audit", icon: "📋" },
  { label: "Controls", href: "/finance/controls", icon: "🛡️" },
];

export function FinanceShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Finance"
      personaIcon="💰"
      accentColor="bg-emerald-100 text-emerald-800"
      accentHover="hover:bg-emerald-100"
      navItems={FINANCE_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
