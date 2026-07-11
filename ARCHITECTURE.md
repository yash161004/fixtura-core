# Architecture

## Design principle

Permission checking and recording are **cross-cutting concerns**, not pipeline stages. Every tool call — allowed or denied — passes through both. If a call is denied, it must still appear in the trace. This is the most common mistake in beginner agent-runtime designs: bolting permission checks onto individual tools instead of centralizing them.

## Components (v1)

### 1. Tool Execution Layer
A small number of well-built tools (target: 4–5 for v1 — e.g., filesystem read/write, a database tool, one external API tool). Each tool declares:
- input schema (validated before execution)
- whether it's idempotent (safe to retry)
- whether it's reversible (safe to undo)

### 2. Permission Engine
Capability-scoped authorization. Answers: **"can this agent session do this?"** Not a global API key — each session gets a scoped capability token (e.g., "read-only on `/workspace`, no DB writes"). Every tool call goes through this before execution.

### 3. Execution Recorder + Sanitizer
Records every step: the exact LLM prompt/completion, the exact tool call arguments and response, timing, and the permission decision. Before anything is persisted, it passes through the **Sanitizer**:

```yaml
persist:
  - tool_name
  - latency
  - token_usage
  - status
redact:
  - authorization
  - api_key
  - password
  - secret
  - bearer
  - cookie
truncate:
  - prompt > 20KB
  - response > 50KB
```

This exists because "record everything" directly conflicts with the project's own security story if secrets flow through tool arguments/responses unredacted. Do not skip this component.

### 4. Replay Runtime
Two v1 modes:
- **Passive Replay** — reproduces the recorded run exactly. Nothing external executes; every LLM completion and tool response is substituted from the recording, not re-invoked.
- **Step Inspection** — pause after every step, inspect prompt/completion/args/response/tokens/timing, then continue manually.

(Counterfactual/branching replay is v1.1 — see ROADMAP.md.)

### 5. Trace Viewer UI
Deliberately minimal. Answers only: what happened, in what order, which tool, how long, was it allowed, what was recorded. No dashboard polish in v1 — that's explicitly out of scope (UI can consume 2-3 weeks if left unbounded).

### 6. OpenEval Adapter
A new adapter (same pattern as OpenEval's existing LangChain/OpenAI adapters) that converts Fixtura's recorded `.trace` format into OpenEval's `AgentTrace` objects, so OpenEval's existing metrics (Tool Selection Accuracy, Argument Correctness, Step Efficiency, Goal Completion Rate) run against real recorded runs.

## Data flow

```
Live Execution
  LLM → Tool Executor → Permission Engine (allow/deny) → [Filesystem | DB | API]
                              │
                              ▼
                     Execution Recorder
                              │
                              ▼
                        Sanitizer
                              │
                              ▼
                  Replay Artifact (.trace file — JSONL, zstd-compressed)

Later — Replay Mode
  .trace → Replay Runtime → recorded LLM output + recorded tool output (substituted, nothing external executes) → Trace Viewer UI
                                                                                                                  → OpenEval Adapter → eval report
```

## Storage

`.trace` artifacts: JSONL internally, zstd-compressed, one artifact per run. Retention policy (last N runs / N days) is configurable but not architecturally solved in v1 — the abstraction is what matters; backend can be swapped later.

## Why not build more (six-engine "AgentOS" idea, rejected)

An earlier draft of this project considered adding a Planning Engine, Memory Engine, Cost Optimizer, Multi-Agent Communication, and a Tool Selector. All were cut for v1:
- **Tool Selector**: not well-motivated at 4–5 tools; the LLM already selects adequately at this scale.
- **Memory Engine**: retrieval/ranking/forgetting/staleness is a research-scale problem on its own — explicitly future work.
- **Cost Optimizer**: without a defined objective function this is just heuristics; postponed.
- **Multi-agent Communication**: doesn't strengthen the debugging story this project is actually about.

This isn't just a v1 scoping call — it's a standing position, revisited and reconfirmed as of mid-2026. The orchestration/memory space has matured substantially since the original cut: LangGraph, CrewAI, Microsoft Agent Framework, Google ADK, and the OpenAI Agents SDK now cover planning, tool routing, and multi-agent coordination; Mem0, Zep, and Letta cover memory with published benchmarks. Rebuilding any of that would mean competing directly with funded, adopted incumbents on their own turf — not filling a gap.

Fixtura's position is the layer underneath those frameworks, not a competitor to them: **deterministic execution recording, replay, and evaluation** — framework-agnostic, so it stays useful regardless of which orchestration tool sits on top. See `ROADMAP.md`'s v1.1 section for the resulting scope decision (a single LangGraph adapter, gated on real demand, not a general integration push).

### What Fixtura is not

To keep this from drifting back toward the AgentOS shape:
- Not an orchestration framework — doesn't decide what an agent does next
- Not a memory system — doesn't store or retrieve context across sessions
- Not a hosted dashboard or SaaS platform — no login, no multi-tenant UI
- Not a cost optimizer or model router
- Not a destination other tools plug into — it's the layer that plugs into them

See `ROADMAP.md` for the authoritative frozen scope.
