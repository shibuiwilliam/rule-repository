"use client";

import { PersonaLayout, type NavItem } from "@/components/PersonaLayout";

const MARKETING_NAV: NavItem[] = [
  { label: "Dashboard", href: "/marketing", icon: "📊" },
  { label: "Creative Review", href: "/marketing/creatives", icon: "🎨" },
  { label: "Ad Compliance", href: "/marketing/ads", icon: "📰" },
  { label: "Brand Rules", href: "/marketing/brand", icon: "⭐" },
  { label: "Campaign Audit", href: "/marketing/campaigns", icon: "📈" },
];

export function MarketingShell({ children }: { children: React.ReactNode }) {
  return (
    <PersonaLayout
      persona="Marketing"
      personaIcon="📣"
      accentColor="bg-purple-100 text-purple-800"
      accentHover="hover:bg-purple-100"
      navItems={MARKETING_NAV}
    >
      {children}
    </PersonaLayout>
  );
}
