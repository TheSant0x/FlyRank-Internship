import express from "express";
import { randomUUID } from "node:crypto";
import { serve } from "inngest/express";
import { executeWorkflow, inngest, runs, type WorkflowInput } from "./workflow.js";

const app = express();
const port = Number(process.env.PORT ?? 3001);
app.use(express.json({ limit: "1mb" }));
app.use((request, response, next) => {
  response.setHeader("access-control-allow-origin", "*");
  response.setHeader("access-control-allow-headers", "content-type");
  if (request.method === "OPTIONS") return response.sendStatus(204);
  next();
});

app.get("/api/health", (_request, response) => response.json({ status: "ok", service: "inngest-gateway" }));

app.post("/api/workflows/run", async (request, response) => {
  const { nodes, edges, context } = request.body as Partial<WorkflowInput>;
  if (!Array.isArray(nodes) || !Array.isArray(edges) || nodes.length === 0 || typeof context !== "string") {
    return response.status(400).json({ message: "nodes, edges, and context are required" });
  }
  const runId = randomUUID();
  runs.set(runId, { runId, status: "queued", logs: [] });
  try {
    await inngest.send({ name: "branchline/workflow.run", data: { runId, nodes, edges, context } });
    return response.status(202).json({ runId });
  } catch (error) {
    runs.delete(runId);
    return response.status(503).json({ message: `Could not queue workflow: ${error instanceof Error ? error.message : "unknown error"}` });
  }
});

app.get("/api/workflows/runs/:runId", (request, response) => {
  const run = runs.get(request.params.runId);
  return run ? response.json(run) : response.status(404).json({ message: "Run not found" });
});

app.use("/api/inngest", serve({ client: inngest, functions: [executeWorkflow] }));
app.listen(port, () => console.log(`Inngest gateway listening on http://127.0.0.1:${port}`));
