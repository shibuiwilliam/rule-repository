"use client";

/**
 * Rule relationship graph visualization using React Flow.
 * Renders rule nodes and their relationships (REFINES, OVERRIDES, etc.)
 */

import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
  Position,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

import type { GraphData } from "@/lib/api";

const RELATIONSHIP_COLORS: Record<string, string> = {
  REFINES: "#3b82f6",
  OVERRIDES: "#ef4444",
  CONFLICTS_WITH: "#f97316",
  DEPENDS_ON: "#8b5cf6",
  DERIVES_FROM: "#06b6d4",
  SUCCEEDS: "#22c55e",
};

interface RuleGraphProps {
  data: GraphData;
  currentRuleId: string;
}

function graphToFlow(data: GraphData, currentRuleId: string) {
  const nodes: Node[] = data.nodes
    .filter((n) => n.id)
    .map((n, i) => ({
      id: n.id,
      position: { x: (i % 4) * 250, y: Math.floor(i / 4) * 120 },
      data: {
        label: n.properties?.statement_preview || n.id.slice(0, 8),
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: {
        background: n.id === currentRuleId ? "#dbeafe" : "#fff",
        border: n.id === currentRuleId ? "2px solid #3b82f6" : "1px solid #d1d5db",
        borderRadius: "8px",
        padding: "8px 12px",
        fontSize: "12px",
        maxWidth: "200px",
      },
    }));

  const edges: Edge[] = data.edges
    .filter((e) => e.source && e.target)
    .map((e, i) => ({
      id: `e-${i}`,
      source: e.source,
      target: e.target,
      label: e.type,
      labelStyle: { fontSize: 10, fill: "#6b7280" },
      style: { stroke: RELATIONSHIP_COLORS[e.type] ?? "#9ca3af" },
      animated: e.type === "CONFLICTS_WITH",
    }));

  return { nodes, edges };
}

export default function RuleGraph({ data, currentRuleId }: RuleGraphProps) {
  const { nodes: initialNodes, edges: initialEdges } = graphToFlow(data, currentRuleId);
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  if (data.nodes.length === 0 && data.edges.length === 0) {
    return <p className="text-sm text-gray-500">No relationships to display.</p>;
  }

  return (
    <div className="h-[300px] w-full rounded-lg border bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
