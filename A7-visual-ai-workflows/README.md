# Branchline — visual AI workflows

Branchline is a small visual workflow studio. Each node asks one AI question and returns exactly `YES` or `NO`; the selected edge determines the next node. The canvas is built with React Flow, durable execution is registered with Inngest, and a Python/FastAPI service owns the model call and its closed decision contract.

## Run it

The project uses a React/Vite frontend, a Node Inngest gateway, and a Python decision service.

```bash
cp .env.example .env
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r requirements-dev.txt
npm install
```

Start three terminals from this directory:

```bash
# terminal 1 — Python decision service
AI_STUB=1 uvicorn backend.main:app --reload --port 8000

# terminal 2 — Inngest gateway
npm run server

# terminal 3 — Inngest local dashboard and event runner
npm run inngest
```

Open the URL printed by Vite after running `npm run dev` in a fourth terminal. Inngest's local dashboard should show `execute-visual-workflow` after the gateway registers it. The default stub mode needs no API key. For a real OpenAI-compatible provider, set `AI_STUB=0`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` in `.env`.

## Using the editor

1. Select a node and edit its name and yes/no question in the inspector.
2. Drag from a node's green YES or orange NO handle to another node. The handle becomes the edge label.
3. Enter the incoming message in **Execution input** and press **Run workflow**.
4. Inngest queues the event, executes one durable step per node, and the UI polls the run log. The active node and edge are highlighted as decisions arrive.
5. Use Reset, Export, Import, and local save to manage the graph. The browser stores the current graph under `branchline:workflow:v1`.

## Contract and structure

- `frontend/`: React Flow editor, node inspector, local graph persistence, execution state and logs.
- `backend/main.py`: FastAPI `/api/decide` service. Its response is `{ "decision": "YES" | "NO", "model": "..." }`.
- `server/workflow.ts`: Inngest function. It starts at the first node, calls one `step.run` per node, records execution order, and follows the matching YES/NO edge.
- `server/index.ts`: queue and polling API plus the `/api/inngest` registration endpoint.
- `ai-version/`: not used; this assignment did not require a generated comparison branch.

The Python service checks that real model output is exactly YES or NO after normalization and returns a provider error rather than silently choosing a branch. OpenAI SDK retries are disabled; Inngest supplies bounded function retries for failed steps. The client-facing editor never treats an arbitrary model string as a decision.

## Optional polish included

This implementation includes more than the required three polish items: visual execution state, an execution log panel, local save/load, JSON import/export, styled decision nodes, explicit error states, durable retries through Inngest, and animated active edges.

## Verification

The frontend helper tests, Python service tests, TypeScript checks, production build, and in-process API checks are run with:

```bash
npm test
pytest -q backend/test_main.py
npm run build
```

No screenshot is committed; the generated PDF and runtime artifacts remain ignored.
