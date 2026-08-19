import type { Edge, Node } from "@xyflow/react";

export type Branch = "YES" | "NO";
export type NodeStatus = "idle" | "queued" | "running" | "yes" | "no" | "error";

export type DecisionNodeData = {
  label: string;
  prompt: string;
  status: NodeStatus;
  lastDecision?: Branch;
  [key: string]: unknown;
};

export type DecisionNode = Node<DecisionNodeData, "decision">;
export type DecisionEdge = Edge<{ branch: Branch }>;

export type WorkflowSnapshot = {
  nodes: DecisionNode[];
  edges: DecisionEdge[];
};

export type RunLog = { nodeId: string; label: string; decision: Branch; timestamp: string };
export type RunState = { runId: string; status: "queued" | "running" | "completed" | "failed"; currentNodeId?: string; logs: RunLog[]; error?: string };
