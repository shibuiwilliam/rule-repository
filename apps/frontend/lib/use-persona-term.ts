"use client";

import { usePathname } from "next/navigation";
import { useMemo } from "react";

import { engineeringVocabulary } from "@/app/(dashboard)/vocabulary";
import { legalVocabulary } from "@/app/(legal)/vocabulary";
import { hrVocabulary } from "@/app/(hr)/vocabulary";
import { financeVocabulary } from "@/app/(finance)/vocabulary";
import { salesVocabulary } from "@/app/(sales)/vocabulary";
import { complianceVocabulary } from "@/app/(compliance)/vocabulary";

type Vocabulary = Record<string, string>;

const PERSONA_VOCABULARIES: Record<string, Vocabulary> = {
  dashboard: engineeringVocabulary,
  engineering: engineeringVocabulary,
  legal: legalVocabulary,
  hr: hrVocabulary,
  finance: financeVocabulary,
  sales: salesVocabulary,
  compliance: complianceVocabulary,
};

/**
 * URL path segments that belong to the engineering/dashboard persona
 * but do not literally match "dashboard" or "engineering".
 * These are routes under the (dashboard) route group.
 */
const DASHBOARD_SEGMENTS = new Set([
  "rules",
  "search",
  "review",
  "playground",
  "discover",
  "intelligence",
  "feedback",
  "federations",
  "proposals",
  "snapshots",
  "ask",
  "assistant",
  "audit",
  "departments",
  "documents",
  "gateway",
  "onboarding",
  "projects",
  "tutor",
]);

/**
 * Detect the current persona from the URL pathname.
 *
 * Route groups like (dashboard) are invisible in the URL. The first path
 * segment is the actual route directory inside the group. We match it
 * against known persona prefixes and fall back to engineering/dashboard.
 */
function detectPersona(pathname: string): string {
  const segments = pathname.split("/").filter(Boolean);
  const first = segments[0] ?? "dashboard";

  if (first in PERSONA_VOCABULARIES) {
    return first;
  }

  // Routes that live inside the (dashboard) group but whose first segment
  // is not literally "dashboard" (e.g. /rules, /search, /playground).
  if (DASHBOARD_SEGMENTS.has(first)) {
    return "dashboard";
  }

  return "dashboard";
}

/**
 * Hook that returns a function to look up persona-specific terminology.
 *
 * Usage:
 *   const t = usePersonaTerm();
 *   <h1>{t("landing_title")}</h1>
 *   // Engineering persona: "Code Compliance Dashboard"
 *   // Legal persona:       "Contract Review Queue"
 */
export function usePersonaTerm(): (key: string, fallback?: string) => string {
  const pathname = usePathname();

  const vocab = useMemo(() => {
    const persona = detectPersona(pathname);
    return PERSONA_VOCABULARIES[persona] ?? engineeringVocabulary;
  }, [pathname]);

  return (key: string, fallback?: string) => {
    return vocab[key] ?? fallback ?? key;
  };
}

/**
 * Get the current persona identifier from the URL.
 *
 * Returns the canonical persona key (e.g. "dashboard", "legal", "hr").
 */
export function useCurrentPersona(): string {
  const pathname = usePathname();
  return detectPersona(pathname);
}
