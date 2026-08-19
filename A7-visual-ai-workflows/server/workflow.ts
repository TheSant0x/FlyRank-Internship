import { Inngest } from "inngest";

export type Branch = "YES" | "NO";
export type WorkflowNode = { id: string; data: { label: string; prompt: string } };
export type WorkflowEdge = { id: string; source: string; target: string; sourceHandle?: string; data?: { branch?: Branch } };
export type WorkflowInput = { runId: string; nodes: WorkflowNode[]; edges: WorkflowEdge[]; context: string };
export type LogEntry = { nodeId: string; label: string; decision: Branch; timestamp: string };
export type RunState = { runId: string; status: "queued" | "running" | "completed" | "failed"; currentNodeId?: string; logs: LogEntry[]; error?: string };

export const inngest = new Inngest({ id: "branchline-workflows" });
export const runs = new Map<string, RunState>();

function nextEdge(edges: WorkflowEdge[], nodeId: string, branch: Branch) {
  return edges.find((edge) => edge.source === nodeId && (edge.data?.branch ?? edge.sourceHandle) === branch);
}

function startNode(nodes: WorkflowNode[], edges: WorkflowEdge[]) {
  const targets = new Set(edges.map((edge) => edge.target));
  return nodes.find((node) => !targets.has(node.id)) ?? nodes[0];
}

function safeStepId(nodeId: string) {
  return nodeId.replace(/[^a-zA-Z0-9_-]/g, "-");
}

export const executeWorkflow = inngest.createFunction(
  { id: "execute-visual-workflow", retries: 2 },
  { event: "branchline/workflow.run" },
  async ({ event, step }) => {
    const input = event.data as WorkflowInput;
    const run = runs.get(input.runId);
    if (!run) throw new Error("Run not found");
    run.status = "running";
    const logs: LogEntry[] = [];
    let node: WorkflowNode | undefined = startNode(input.nodes, input.edges);
    const visited = new Set<string>();

    while (node && !visited.has(node.id)) {
      const currentNode = node;
      visited.add(currentNode.id);
      run.currentNodeId = currentNode.id;
      const decision = await step.run(`decide-${safeStepId(currentNode.id)}`, async () => {
        const response = await fetch(`${process.env.PYTHON_API_URL ?? "http://127.0.0.1:8000"}/api/decide`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ prompt: currentNode.data.prompt, context: input.context }),
        });
        if (!response.ok) throw new Error(`Decision service returned ${response.status}`);
        const body = await response.json() as { decision?: Branch };
        if (body.decision !== "YES" && body.decision !== "NO") throw new Error("Decision service returned an invalid branch");
        return body.decision;
      });
      const entry = { nodeId: currentNode.id, label: currentNode.data.label, decision, timestamp: new Date().toISOString() };
      logs.push(entry);
      run.logs = [...logs];
      const edge = nextEdge(input.edges, currentNode.id, decision);
      node = edge ? input.nodes.find((candidate) => candidate.id === edge.target) : undefined;
    }
    run.currentNodeId = undefined;
    run.status = "completed";
    return { runId: input.runId, logs };
  },
);
