# Fixtura

**Deterministic execution recording and replay for AI agents — turn real agent runs into regression tests.**

## What this is

Fixtura watches an AI agent's tool calls (filesystem, database, API, etc.), records everything that happens through a permission-checked execution layer, and lets you replay that recording later — deterministically, without touching live systems — to debug failures or gate CI on regressions.

It's built to work with **OpenEval**, a deterministic (non-LLM-judge) agent evaluation engine already built and published separately. Fixtura produces the recordings; OpenEval scores them.

## Why this exists

Most "agent observability" tools (Langfuse, Phoenix, Braintrust, Laminar) are built for production monitoring at scale. Fixtura's angle is narrower and more testable: **recorded traces as literal test fixtures**, replayable offline, usable to gate pull requests the same way unit test snapshots do. See ARCHITECTURE.md for why this is scoped the way it is, and what was deliberately cut.

## Status

✅ v1.0.0 is released. See ROADMAP.md for future features like counterfactual replay (Live Branching).

## OpenEval Adapter (optional, manual install required)

The OpenEval evaluation harness (Acceptance Test 4) relies on OpenEval, which is currently unpublished on PyPI. Note that the openeval namespace on PyPI is occupied by an unrelated placeholder package. 

To use the OpenEval Adapter, you must manually install OpenEval via git:
`ash
pip install git+https://github.com/yash161004/OpenEval.git@4cb6cfe362c770a7674f5b0111ff54646883709b
`
Without this, pip install fixtura will give you the core recording, permissions, and replay capabilities, but importing ixtura.tools.openeval_adapter will raise a clear RuntimeError prompting this manual installation.

## Documents in this repo

| Doc | Purpose |
|---|---|
| ARCHITECTURE.md | System design, components, data flow |
| THREAT_MODEL.md | Trust boundaries, what could go wrong, mitigations |
| ROADMAP.md | Frozen v1 scope table + acceptance tests + v1.1/v2 future work |
| docs/TRACE_FORMAT_SPEC.md | Exact schema every recording must produce |
| docs/COLLABORATION.md | How the owner, Claude, ChatGPT, and Antigravity work together on this project |

## Core components

1. Tool Execution Layer
2. Permission Engine
3. Execution Recorder + Sanitizer
4. Passive Replay + Step Inspection
5. Trace Viewer UI (minimal)
6. OpenEval adapter (evaluation harness reuse)

## License

[MIT License](LICENSE)
