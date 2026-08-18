import { Activity, GitBranch, Play, Plus, Settings2 } from "lucide-react";
import { Button } from "./components/ui/button";

export function App() {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark"><GitBranch size={17} /></span><span>branchline</span><span className="eyebrow">WORKFLOW STUDIO</span></div>
        <div className="topbar-actions"><span className="status-dot" />All systems nominal <Button size="sm" variant="ghost"><Settings2 size={15} /> Settings</Button></div>
      </header>
      <section className="workspace-heading">
        <div><p className="eyebrow">WORKSPACE / UNTITLED</p><h1>Visual decision workflow</h1><p className="lede">Build a branching path where every AI decision is a simple yes or no.</p></div>
        <div className="heading-actions"><Button><Plus size={16} /> Add node</Button><Button variant="primary"><Play size={15} /> Run workflow</Button></div>
      </section>
      <section className="setup-placeholder"><Activity size={18} /><div><strong>Editor ready</strong><span>Add a decision node to start designing your workflow.</span></div></section>
    </main>
  );
}
