# Fixtura

**Deterministic execution recording and replay for AI agents — turn real agent runs into regression tests.**

## What this is

Fixtura watches an AI agent's tool calls (filesystem, database, API, etc.), records everything that happens through a permission-checked execution layer, and lets you replay that recording later — deterministically, without touching live systems — to debug failures or gate CI on regressions.

It's built to work with **[OpenEval](../openeval)**, a deterministic (non-LLM-judge) agent evaluation engine already built and published separately. Fixtura produces the recordings; OpenEval scores them.

## Why this exists

Most "agent observability" tools (Langfuse, Phoenix, Braintrust, Laminar) are built for production monitoring at scale. Fixtura's angle is narrower and more testable: **recorded traces as literal test fixtures**, replayable offline, usable to gate pull requests the same way unit test snapshots do. See `ARCHITECTURE.md` for why this is scoped the way it is, and what was deliberately cut.

## Status

📋 Planning complete. Build not yet started. See `ROADMAP.md` for the frozen v1 scope — nothing outside that table gets built until v1 ships.

## Documents in this repo

| Doc | Purpose |
|---|---|
| `ARCHITECTURE.md` | System design, components, data flow |
| `THREAT_MODEL.md` | Trust boundaries, what could go wrong, mitigations |
| `ROADMAP.md` | Frozen v1 scope table + acceptance tests + v1.1/v2 future work |
| `docs/TRACE_FORMAT_SPEC.md` | Exact schema every recording must produce (must satisfy OpenEval's `AgentTrace`) |
| `docs/PHASE_1_INSTRUCTIONS.md` | The current build order given to Antigravity — read this if you're implementing |
| `docs/COLLABORATION.md` | How the owner (Yashrajsinh), Claude, ChatGPT, and Antigravity work together on this project |

## Core components (v1 only — see ROADMAP.md)

1. Tool Execution Layer
2. Permission Engine
3. Execution Recorder + Sanitizer
4. Passive Replay + Step Inspection
5. Trace Viewer UI (minimal)
6. OpenEval adapter (evaluation harness reuse)

## License

TBD — recommend Apache-2.0 or MIT for an open-source developer tool (permissive, widely trusted, matches OpenEval's licensing if applicable).
