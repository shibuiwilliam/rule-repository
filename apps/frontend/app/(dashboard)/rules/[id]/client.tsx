"use client";

/**
 * Client-side interactive parts of the rule detail page:
 * - Edit button + modal
 * - Relationship graph visualization
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import RuleEditForm from "@/components/RuleEditForm";
import type { Rule, GraphData } from "@/lib/api";

// Lazy-load React Flow to avoid SSR issues
const RuleGraph = dynamic(() => import("@/components/RuleGraph"), { ssr: false });

interface RuleDetailClientProps {
  rule: Rule;
  graph?: GraphData;
  showGraph?: boolean;
}

export default function RuleDetailClient({ rule, graph, showGraph }: RuleDetailClientProps) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);

  if (showGraph && graph) {
    return <RuleGraph data={graph} currentRuleId={rule.id} />;
  }

  return (
    <>
      <button
        onClick={() => setEditing(true)}
        className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
      >
        Edit
      </button>

      {editing && (
        <RuleEditForm
          rule={rule}
          onSaved={() => {
            setEditing(false);
            router.refresh();
          }}
          onCancel={() => setEditing(false)}
        />
      )}
    </>
  );
}
