"use client";

/**
 * Norm Lineage Viewer — interactive visualization of the norm hierarchy.
 *
 * Renders the chain from operational rules up to source laws/regulations
 * (upstream) or down to derived department rules (downstream).
 * Uses React Flow for the graph layout.
 */

import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  MarkerType,
  type Node,
  Position,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

/* ---------- types ---------- */

export interface LineageNode {
  rule_id: string;
  statement: string;
  norm_tier: string;
  norm_authority: string | null;
  depth: number;
}

export interface LineageChain {
  root_rule_id: string;
  nodes: LineageNode[];
  direction: "upstream" | "downstream";
}

interface NormLineageViewerProps {
  ruleId: string;
  /** Pre-fetched data; if omitted the component fetches from the API. */
  upstream?: LineageChain | null;
  downstream?: LineageChain | null;
  apiBase?: string;
}

/* ---------- constants ---------- */

const TIER_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  LAW:               { bg: "#fef2f2", border: "#ef4444", text: "#991b1b" },
  REGULATION:        { bg: "#fff7ed", border: "#f97316", text: "#9a3412" },
  GUIDELINE:         { bg: "#fefce8", border: "#eab308", text: "#854d0e" },
  CORPORATE_POLICY:  { bg: "#f0fdf4", border: "#22c55e", text: "#166534" },
  DEPARTMENT_RULE:   { bg: "#eff6ff", border: "#3b82f6", text: "#1e40af" },
  OPERATIONAL_RULE:  { bg: "#f5f3ff", border: "#8b5cf6", text: "#5b21b6" },
};

const TIER_LABELS: Record<string, string> = {
  LAW: "Law",
  REGULATION: "Regulation",
  GUIDELINE: "Guideline",
  CORPORATE_POLICY: "Corporate Policy",
  DEPARTMENT_RULE: "Department Rule",
  OPERATIONAL_RULE: "Operational Rule",
};

const NODE_WIDTH = 320;
const Y_GAP = 140;

/* ---------- helpers ---------- */

function buildGraphData(
  rootId: string,
  upstream: LineageChain | null,
  downstream: LineageChain | null,
): { nodes: Node[]; edges: Edge[] } {
  const nodeMap = new Map<string, LineageNode>();
  const edgeList: Edge[] = [];

  // Collect all unique nodes
  const allNodes: LineageNode[] = [];

  if (upstream) {
    for (const n of upstream.nodes) {
      if (!nodeMap.has(n.rule_id)) {
        nodeMap.set(n.rule_id, n);
        allNodes.push(n);
      }
    }
  }

  if (downstream) {
    for (const n of downstream.nodes) {
      if (!nodeMap.has(n.rule_id)) {
        nodeMap.set(n.rule_id, n);
        allNodes.push(n);
      }
    }
  }

  // Ensure root node exists
  if (!nodeMap.has(rootId)) {
    const rootNode: LineageNode = {
      rule_id: rootId,
      statement: "(current rule)",
      norm_tier: "OPERATIONAL_RULE",
      norm_authority: null,
      depth: 0,
    };
    nodeMap.set(rootId, rootNode);
    allNodes.push(rootNode);
  }

  // Sort upstream nodes by depth descending (highest tier first), downstream ascending
  const upstreamNodes = (upstream?.nodes ?? [])
    .filter((n) => n.rule_id !== rootId)
    .sort((a, b) => b.depth - a.depth);
  const downstreamNodes = (downstream?.nodes ?? [])
    .filter((n) => n.rule_id !== rootId)
    .sort((a, b) => a.depth - b.depth);

  // Position nodes vertically: upstream above root, downstream below
  const rootY = upstreamNodes.length * Y_GAP;
  const nodes: Node[] = [];

  upstreamNodes.forEach((n, i) => {
    const colors = TIER_COLORS[n.norm_tier] ?? TIER_COLORS.OPERATIONAL_RULE;
    nodes.push({
      id: n.rule_id,
      position: { x: 0, y: i * Y_GAP },
      data: { label: n, isRoot: false },
      type: "lineageNode",
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      style: {
        width: NODE_WIDTH,
        background: colors.bg,
        border: `2px solid ${colors.border}`,
        borderRadius: 12,
        padding: 12,
      },
    });
  });

  // Root node
  const rootData = nodeMap.get(rootId)!;
  const rootColors = TIER_COLORS[rootData.norm_tier] ?? TIER_COLORS.OPERATIONAL_RULE;
  nodes.push({
    id: rootId,
    position: { x: 0, y: rootY },
    data: { label: rootData, isRoot: true },
    type: "lineageNode",
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    style: {
      width: NODE_WIDTH,
      background: rootColors.bg,
      border: `3px solid ${rootColors.border}`,
      borderRadius: 12,
      padding: 12,
      boxShadow: "0 0 0 4px rgba(59, 130, 246, 0.15)",
    },
  });

  downstreamNodes.forEach((n, i) => {
    const colors = TIER_COLORS[n.norm_tier] ?? TIER_COLORS.OPERATIONAL_RULE;
    nodes.push({
      id: n.rule_id,
      position: { x: 0, y: rootY + (i + 1) * Y_GAP },
      data: { label: n, isRoot: false },
      type: "lineageNode",
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      style: {
        width: NODE_WIDTH,
        background: colors.bg,
        border: `2px solid ${colors.border}`,
        borderRadius: 12,
        padding: 12,
      },
    });
  });

  // Build edges: upstream chain flows downward (parent → child)
  if (upstream && upstream.nodes.length > 1) {
    const sorted = [...upstream.nodes].sort((a, b) => b.depth - a.depth);
    for (let i = 0; i < sorted.length - 1; i++) {
      edgeList.push({
        id: `e-${sorted[i].rule_id}-${sorted[i + 1].rule_id}`,
        source: sorted[i].rule_id,
        target: sorted[i + 1].rule_id,
        label: "DERIVES_FROM",
        style: { stroke: "#06b6d4", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#06b6d4" },
        animated: false,
      });
    }
  }

  // Downstream edges
  if (downstream && downstream.nodes.length > 1) {
    const sorted = [rootData, ...downstream.nodes.filter((n) => n.rule_id !== rootId)].sort(
      (a, b) => a.depth - b.depth,
    );
    for (let i = 0; i < sorted.length - 1; i++) {
      edgeList.push({
        id: `e-${sorted[i].rule_id}-${sorted[i + 1].rule_id}`,
        source: sorted[i].rule_id,
        target: sorted[i + 1].rule_id,
        label: "DERIVES_FROM",
        style: { stroke: "#06b6d4", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#06b6d4" },
        animated: false,
      });
    }
  }

  return { nodes, edges: edgeList };
}

/* ---------- custom node ---------- */

function LineageNodeComponent({ data }: { data: { label: LineageNode; isRoot: boolean } }) {
  const node = data.label;
  const tierLabel = TIER_LABELS[node.norm_tier] ?? node.norm_tier;
  const colors = TIER_COLORS[node.norm_tier] ?? TIER_COLORS.OPERATIONAL_RULE;

  return (
    <div className="text-left">
      <div className="flex items-center gap-2">
        <span
          className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
          style={{ backgroundColor: colors.border, color: "#fff" }}
        >
          {tierLabel}
        </span>
        {data.isRoot && (
          <span className="rounded-full bg-blue-500 px-2 py-0.5 text-[10px] font-semibold text-white">
            Current
          </span>
        )}
      </div>
      <p className="mt-1.5 line-clamp-2 text-xs font-medium" style={{ color: colors.text }}>
        {node.statement}
      </p>
      {node.norm_authority && (
        <p className="mt-0.5 truncate text-[10px] text-gray-500">{node.norm_authority}</p>
      )}
    </div>
  );
}

const nodeTypes = { lineageNode: LineageNodeComponent };

/* ---------- main component ---------- */

export default function NormLineageViewer({
  ruleId,
  upstream: upstreamProp,
  downstream: downstreamProp,
  apiBase,
}: NormLineageViewerProps) {
  const [upstream, setUpstream] = useState<LineageChain | null>(upstreamProp ?? null);
  const [downstream, setDownstream] = useState<LineageChain | null>(downstreamProp ?? null);
  const [loading, setLoading] = useState(!upstreamProp && !downstreamProp);
  const [error, setError] = useState<string | null>(null);

  const base = apiBase ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  useEffect(() => {
    if (upstreamProp || downstreamProp) return;

    let cancelled = false;
    async function fetchLineage() {
      try {
        const [upRes, downRes] = await Promise.all([
          fetch(`${base}/api/v1/lineage/${ruleId}/upstream`),
          fetch(`${base}/api/v1/lineage/${ruleId}/downstream`),
        ]);
        if (!cancelled) {
          if (upRes.ok) setUpstream(await upRes.json());
          if (downRes.ok) setDownstream(await downRes.json());
        }
      } catch {
        if (!cancelled) setError("Failed to load norm lineage data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchLineage();
    return () => { cancelled = true; };
  }, [ruleId, base, upstreamProp, downstreamProp]);

  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildGraphData(ruleId, upstream, downstream),
    [ruleId, upstream, downstream],
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const totalNodes = (upstream?.nodes.length ?? 0) + (downstream?.nodes.length ?? 0);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border bg-white">
        <p className="text-sm text-gray-400">Loading norm lineage...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border bg-white">
        <p className="text-sm text-red-500">{error}</p>
      </div>
    );
  }

  if (totalNodes === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border bg-white">
        <p className="text-sm text-gray-400">No norm lineage data found for this rule.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Legend */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(TIER_LABELS).map(([tier, label]) => {
          const colors = TIER_COLORS[tier];
          return (
            <span
              key={tier}
              className="rounded-full px-2.5 py-0.5 text-[10px] font-medium"
              style={{
                backgroundColor: colors.bg,
                border: `1px solid ${colors.border}`,
                color: colors.text,
              }}
            >
              {label}
            </span>
          );
        })}
      </div>

      {/* Graph */}
      <div className="h-[500px] rounded-xl border bg-white">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={16} size={1} />
          <Controls />
        </ReactFlow>
      </div>

      {/* Summary */}
      <div className="flex gap-4 text-xs text-gray-500">
        <span>{upstream?.nodes.length ?? 0} upstream norm(s)</span>
        <span>{downstream?.nodes.length ?? 0} downstream derivative(s)</span>
      </div>
    </div>
  );
}
