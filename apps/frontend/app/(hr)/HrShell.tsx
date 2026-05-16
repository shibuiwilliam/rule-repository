"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const HR_NAV: NavItem[] = [
  { label: "Dashboard", href: "/hr", icon: "📊" },
  { label: "Violations", href: "/hr/violations", icon: "⚠️" },
  { label: "Attendance", href: "/hr/attendance", icon: "⏰" },
  { label: "Leave Management", href: "/hr/leave", icon: "🏖️" },
  { label: "Employee Lifecycle", href: "/hr/lifecycle", icon: "🔄" },
  { label: "Compliance Reports", href: "/hr/reports", icon: "📋" },
  { label: "Policy Library", href: "/hr/policies", icon: "📚" },
  { label: "HRIS Status", href: "/hr/hris", icon: "⚙️" },
];

export function HrShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="HR"
      personaIcon="👥"
      accentColor="bg-indigo-100 text-indigo-800"
      accentHover="hover:bg-indigo-100"
      navItems={HR_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
