import type { Connection } from "@xyflow/react";
import type { DecisionEdge, DecisionNode, WorkflowSnapshot } from "../types";

export const STORAGE_KEY = "branchline:workflow:v1";

export const initialNodes: DecisionNode[] = [
  {
    id: "support-check",
    type: "decision",
    position: { x: 120, y: 150 },
    data: { label: "Support request?", prompt: "Is this message asking for customer support?", status: "idle" },
  },
  {
    id: "support-team",
    type: "decision",
    position: { x: 490, y: 60 },
    data: { label: "Urgent issue?", prompt: "Does this support request describe an urgent problem?", status: "idle" },
  },
  {
    id: "sales-team",
    type: "decision",
    position: { x: 490, y: 255 },
    data: { label: "Sales follow-up", prompt: "Would a product demo help this person?", status: "idle" },
  },
];

export const initialEdges: DecisionEdge[] = [
  { id: "support-yes", source: "support-check", target: "support-team", sourceHandle: "YES", label: "YES", data: { branch: "YES" }, animated: false },
  { id: "support-no", source: "support-check", target: "sales-team", sourceHandle: "NO", label: "NO", data: { branch: "NO" }, animated: false },
];

export function isSnapshot(value: unknown): value is WorkflowSnapshot {
  if (!value || typeof value !== "object") return false;
  const snapshot = value as Partial<WorkflowSnapshot>;
  return Array.isArray(snapshot.nodes) && Array.isArray(snapshot.edges);
}

export function loadSnapshot(): WorkflowSnapshot {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const parsed: unknown = stored ? JSON.parse(stored) : null;
    return isSnapshot(parsed) ? parsed : { nodes: initialNodes, edges: initialEdges };
  } catch {
    return { nodes: initialNodes, edges: initialEdges };
  }
}

export function saveSnapshot(snapshot: WorkflowSnapshot): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
}

export function edgeFromConnection(connection: Connection): DecisionEdge | null {
  if (!connection.source || !connection.target || !connection.sourceHandle) return null;
  const branch = connection.sourceHandle === "YES" || connection.sourceHandle === "NO" ? connection.sourceHandle : null;
  if (!branch) return null;
  return {
    ...connection,
    id: `${connection.source}-${branch.toLowerCase()}-${connection.target}`,
    label: branch,
    data: { branch },
    animated: false,
  };
}
