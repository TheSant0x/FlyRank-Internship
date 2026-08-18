import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Check, Circle, LoaderCircle, X } from "lucide-react";
import type { DecisionNode as DecisionNodeType, DecisionNodeData, NodeStatus } from "../types";

const statusLabel: Record<NodeStatus, string> = {
  idle: "Ready",
  queued: "Queued",
  running: "Running",
  yes: "YES",
  no: "NO",
  error: "Error",
};

export function DecisionNode({ data, selected }: NodeProps<DecisionNodeType>) {
  const status = data.status;
  return (
    <article className={`decision-node node-${status} ${selected ? "node-selected" : ""}`}>
      <Handle type="target" position={Position.Left} className="handle-target" />
      <header className="node-header">
        <span className="node-kicker">AI DECISION</span>
        <span className="node-status" aria-label={`Status: ${statusLabel[status]}`}>
          {status === "running" && <LoaderCircle className="spin" size={13} />}
          {status === "yes" && <Check size={13} />}
          {status === "no" && <X size={13} />}
          {status === "idle" && <Circle size={10} />}
          {statusLabel[status]}
        </span>
      </header>
      <h3>{data.label}</h3>
      <p>{data.prompt}</p>
      <div className="node-branches">
        <span className="branch branch-yes">YES <small>→</small></span>
        <span className="branch branch-no">NO <small>→</small></span>
      </div>
      <Handle type="source" position={Position.Right} id="YES" className="handle-yes" style={{ top: "62%" }} />
      <Handle type="source" position={Position.Right} id="NO" className="handle-no" style={{ top: "84%" }} />
    </article>
  );
}
