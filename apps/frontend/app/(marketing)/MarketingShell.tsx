"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const MARKETING_NAV: NavItem[] = [
  { label: "Dashboard", href: "/marketing", icon: "\ud83d\udcca" },
  { label: "Creative Review", href: "/marketing/creatives", icon: "\ud83c\udfa8" },
  { label: "Ad Compliance", href: "/marketing/ads", icon: "\ud83d\udcf0" },
  { label: "Brand Rules", href: "/marketing/brand", icon: "\u2b50" },
  { label: "Campaign Audit", href: "/marketing/campaigns", icon: "\ud83d\udcc8" },
];

export function MarketingShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Marketing"
      personaIcon="\ud83d\udce3"
      accentColor="bg-purple-100 text-purple-800"
      accentHover="hover:bg-purple-100"
      navItems={MARKETING_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
