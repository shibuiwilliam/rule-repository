"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const HR_NAV: NavItem[] = [
  { label: "Dashboard", href: "/hr", icon: "\ud83d\udcca" },
  { label: "Attendance", href: "/hr/attendance", icon: "\u23f0" },
  { label: "Leave Management", href: "/hr/leave", icon: "\ud83c\udfd6\ufe0f" },
  { label: "Compliance Reports", href: "/hr/reports", icon: "\ud83d\udccb" },
  { label: "Policy Library", href: "/hr/policies", icon: "\ud83d\udcda" },
  { label: "HRIS Status", href: "/hr/hris", icon: "\ud83d\udd04" },
];

export function HrShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="HR"
      personaIcon="\ud83d\udc65"
      accentColor="bg-indigo-100 text-indigo-800"
      accentHover="hover:bg-indigo-100"
      navItems={HR_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
