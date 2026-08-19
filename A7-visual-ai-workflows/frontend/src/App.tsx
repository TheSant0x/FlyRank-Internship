import { useCallback, useEffect, useRef, useState } from "react";
import {
  addEdge,
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Connection,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Activity, Download, FileJson, GitBranch, Play, Plus, RotateCcw, Save, Settings2, Upload, X } from "lucide-react";
import { Button } from "./components/ui/button";
import { DecisionNode } from "./components/DecisionNode";
import { edgeFromConnection, initialEdges, initialNodes, loadSnapshot, saveSnapshot } from "./lib/workflow";
import type { DecisionEdge, DecisionNode as DecisionNodeType, DecisionNodeData, RunState, WorkflowSnapshot } from "./types";

const nodeTypes: NodeTypes = { decision: DecisionNode };
const DEFAULT_PROMPT = "Ask a focused yes/no question about the incoming request.";
const DEFAULT_CONTEXT = "A customer sent a support request about their account.";

export function App() {
  const loaded = loadSnapshot();
  const [nodes, setNodes, onNodesChange] = useNodesState<DecisionNodeType>(loaded.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<DecisionEdge>(loaded.edges);
  const [selectedId, setSelectedId] = useState<string | null>(loaded.nodes[0]?.id ?? null);
  const [savedLabel, setSavedLabel] = useState("Saved locally");
  const [importError, setImportError] = useState("");
  const [context, setContext] = useState(DEFAULT_CONTEXT);
  const [run, setRun] = useState<RunState | null>(null);
  const [runError, setRunError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const selectedNode = nodes.find((node) => node.id === selectedId);

  useEffect(() => { saveSnapshot({ nodes, edges }); }, [nodes, edges]);

  const onConnect = useCallback((connection: Connection) => {
    const edge = edgeFromConnection(connection);
    if (edge) setEdges((current) => addEdge(edge, current));
  }, [setEdges]);

  const addDecisionNode = useCallback(() => {
    const index = nodes.length + 1;
    const newNode: DecisionNodeType = {
      id: `decision-${Date.now()}`,
      type: "decision",
      position: { x: 140 + (index % 3) * 290, y: 100 + Math.floor(index / 3) * 210 },
      data: { label: `Decision ${index}`, prompt: DEFAULT_PROMPT, status: "idle" },
    };
    setNodes((current) => [...current, newNode]); setSelectedId(newNode.id);
  }, [nodes.length, setNodes]);

  const updateSelected = (patch: Partial<DecisionNodeData>) => {
    if (!selectedId) return;
    setNodes((current) => current.map((node) => node.id === selectedId ? { ...node, data: { ...node.data, ...patch } } : node));
  };

  const saveNow = () => {
    saveSnapshot({ nodes, edges }); setSavedLabel("Saved just now");
    window.setTimeout(() => setSavedLabel("Saved locally"), 1800);
  };

  const reset = () => {
    setNodes(initialNodes); setEdges(initialEdges); setSelectedId(initialNodes[0].id); setRun(null); setRunError(""); setSavedLabel("Reset to starter");
  };

  const exportJson = () => {
    const blob = new Blob([JSON.stringify({ nodes, edges }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = "branchline-workflow.json"; link.click(); URL.revokeObjectURL(url);
  };

  const importJson = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed: unknown = JSON.parse(String(reader.result));
        if (!parsed || typeof parsed !== "object" || !Array.isArray((parsed as WorkflowSnapshot).nodes) || !Array.isArray((parsed as WorkflowSnapshot).edges)) throw new Error("Expected nodes and edges arrays");
        const snapshot = parsed as WorkflowSnapshot;
        setNodes(snapshot.nodes); setEdges(snapshot.edges); setSelectedId(snapshot.nodes[0]?.id ?? null); setImportError("");
      } catch (error) { setImportError(error instanceof Error ? error.message : "Could not import workflow"); }
    };
    reader.readAsText(file);
  };

  const applyRunState = (state: RunState) => {
    const decisions = new Map(state.logs.map((entry) => [entry.nodeId, entry.decision]));
    setNodes((current) => current.map((node) => {
      const status: DecisionNodeData["status"] = state.currentNodeId === node.id
        ? "running"
        : decisions.has(node.id)
          ? decisions.get(node.id) === "YES" ? "yes" : "no"
          : state.status === "queued" ? "queued" : "idle";
      return { ...node, data: { ...node.data, status, lastDecision: decisions.get(node.id) } };
    }));
    const last = state.logs[state.logs.length - 1];
    setEdges((current) => current.map((edge) => ({ ...edge, animated: Boolean(last && edge.source === last.nodeId && edge.data?.branch === last.decision) })));
  };

  const runWorkflow = async () => {
    setRunError(""); setRun(null);
    setNodes((current) => current.map((node) => ({ ...node, data: { ...node.data, status: "queued", lastDecision: undefined } })));
    try {
      const response = await fetch("/api/workflows/run", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ nodes, edges, context }) });
      const body = await response.json() as { runId?: string; message?: string };
      if (!response.ok || !body.runId) throw new Error(body.message ?? "Could not start workflow");
      let finished = false;
      while (!finished) {
        await new Promise((resolve) => window.setTimeout(resolve, 500));
        const statusResponse = await fetch(`/api/workflows/runs/${body.runId}`);
        if (!statusResponse.ok) throw new Error("Could not read workflow status");
        const state = await statusResponse.json() as RunState;
        setRun(state); applyRunState(state); finished = state.status === "completed" || state.status === "failed";
        if (state.status === "failed") throw new Error(state.error ?? "Workflow failed");
      }
    } catch (error) { setRunError(error instanceof Error ? error.message : "Workflow failed"); setRun((current) => current ? { ...current, status: "failed", error: String(error) } : null); }
  };

  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand"><span className="brand-mark"><GitBranch size={17} /></span><span>branchline</span><span className="eyebrow">WORKFLOW STUDIO</span></div><div className="topbar-actions"><span className="status-dot" />Inngest gateway <Button size="sm" variant="ghost"><Settings2 size={15} /> Settings</Button></div></header>
      <section className="workspace-heading"><div><p className="eyebrow">WORKSPACE / UNTITLED</p><h1>Visual decision workflow</h1><p className="lede">Build a branching path where every AI decision is a simple yes or no.</p></div><div className="heading-actions"><Button onClick={addDecisionNode}><Plus size={16} /> Add node</Button><Button variant="primary" onClick={runWorkflow} disabled={run?.status === "queued" || run?.status === "running"}><Play size={15} /> {run?.status === "running" ? "Running…" : "Run workflow"}</Button></div></section>
      <section className="editor-layout"><div className="canvas-panel"><div className="canvas-toolbar"><div className="canvas-meta"><span className="live-pill"><span />Draft</span><span>{nodes.length} nodes · {edges.length} connections</span></div><div className="canvas-tools"><Button size="sm" variant="ghost" onClick={reset}><RotateCcw size={14} /> Reset</Button><Button size="sm" variant="ghost" onClick={exportJson}><Download size={14} /> Export</Button><Button size="sm" variant="ghost" onClick={() => inputRef.current?.click()}><Upload size={14} /> Import</Button><input ref={inputRef} hidden type="file" accept="application/json" onChange={(event) => event.target.files?.[0] && importJson(event.target.files[0])} /></div></div>{importError && <div className="import-error" role="alert">{importError}<button aria-label="Dismiss import error" onClick={() => setImportError("")}><X size={13} /></button></div>}<div className="flow-wrap"><ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeClick={(_, node) => setSelectedId(node.id)} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.2 }} proOptions={{ hideAttribution: true }}><Background color="#d7dde4" gap={24} size={1} /><Controls showInteractive={false} /><MiniMap nodeColor={(node) => node.id === selectedId ? "#176b5b" : "#aeb8c3"} maskColor="rgba(247,248,250,.7)" /></ReactFlow><div className="canvas-legend"><span><i className="legend-yes" />YES path</span><span><i className="legend-no" />NO path</span></div></div></div>
        <aside className="inspector-panel"><div className="inspector-heading"><div><p className="eyebrow">NODE INSPECTOR</p><h2>{selectedNode ? "Decision details" : "Select a node"}</h2></div><Button size="sm" variant="ghost" aria-label="Inspector settings"><Settings2 size={15} /></Button></div>{selectedNode ? <div className="inspector-body"><label htmlFor="node-label">Node name</label><input id="node-label" value={selectedNode.data.label} onChange={(event) => updateSelected({ label: event.target.value })} /><label htmlFor="node-prompt">Decision prompt</label><textarea id="node-prompt" rows={5} value={selectedNode.data.prompt} onChange={(event) => updateSelected({ prompt: event.target.value })} /><p className="field-help">Ask one question that can be answered with only YES or NO.</p><div className="branch-preview"><div><span className="branch-dot yes" />YES <span>continues on yes</span></div><div><span className="branch-dot no" />NO <span>continues on no</span></div></div><Button className="save-button" variant="primary" onClick={saveNow}><Save size={14} /> Save changes</Button><span className="save-label" role="status">{savedLabel}</span></div> : <div className="empty-inspector">Click a node on the canvas to edit its question.</div>}</aside></section>
      <section className="lower-panels"><div className="run-controls"><div><p className="eyebrow">EXECUTION INPUT</p><h2>What should the workflow decide?</h2></div><div className="context-row"><input aria-label="Workflow context" value={context} onChange={(event) => setContext(event.target.value)} /><Button variant="primary" onClick={runWorkflow} disabled={run?.status === "queued" || run?.status === "running"}><Play size={14} /> Run</Button></div></div><div className="panel-title"><div><p className="eyebrow">EXECUTION LOG</p><h2>Latest run</h2></div><span className="run-id"><FileJson size={14} /> {run ? `${run.status} · ${run.logs.length} decisions` : "No runs yet"}</span></div>{runError && <div className="run-error" role="alert">{runError}</div>}{run?.logs.length ? <div className="log-list">{run.logs.map((entry) => <div className="log-row" key={`${entry.nodeId}-${entry.timestamp}`}><span className="log-node">{entry.label}</span><span className={`log-decision ${entry.decision.toLowerCase()}`}>{entry.decision}</span><span className="log-time">{new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span></div>)}</div> : <div className="empty-log"><Activity size={18} /><div><strong>Ready when you are</strong><span>Run the workflow to see each AI decision appear here.</span></div></div>}</section>
    </main>
  );
}
