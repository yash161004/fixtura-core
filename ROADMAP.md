# Roadmap

## This is a contract, not a suggestion

Anything not in the v1 table below is out of scope until v1 ships and all six acceptance tests pass. New ideas go to "Postponed," not into the current sprint. This exists specifically because this project's design process (documented in the design discussion) repeatedly re-added scope after agreeing to cut it — freezing it in writing is the fix.

## v1 — Build now

| Module | Status |
|---|---|
| Tool Execution Layer (4–5 tools) | ✅ Done |
| Permission Engine | ✅ Done |
| Execution Recorder | ✅ Done |
| Recorder Sanitizer (redact/truncate) | ✅ Done |
| Passive Replay | ✅ Done |
| Step Inspection | ✅ Done |
| OpenEval Adapter | ✅ Done |
| Trace Viewer UI (minimal) | ✅ Done — commit 5d49e0e, CI run #27 (29149996867), green |
| Threat Model / Architecture / ADRs | ✅ Done |
| Test suite | ✅ Done |

## v1.1 — Postponed (do not start until v1 passes all acceptance tests)

- **Positioning: Execution Assurance layer.** Fixtura is not building toward becoming an orchestration framework, a memory system, or a general "Agent OS." That space is mature and well-funded (LangGraph, CrewAI, Mem0, Zep, and others cover planning, memory, tool routing, and multi-agent coordination). Fixtura's scope stays fixed: deterministic execution recording, replay, and evaluation — a layer that sits *underneath* whichever orchestration framework a team already uses, not a replacement for it. This entry exists so no future roadmap re-introduces "Agent OS" as a destination; if that discussion comes up again, it should be evaluated against this note first, not re-litigated from scratch.
- **LangGraph adapter (first and only framework integration for v1.1):**
  - Scope: one adapter, targeting LangGraph specifically — chosen because it has the largest enterprise-weighted install base and exposes native checkpointing/node-transition hooks that give a clean, documented attachment point (lower engineering risk than frameworks with opaque internals).
  - Explicitly NOT in scope for this item: adapters for CrewAI, OpenAI Agents SDK, Google ADK, Microsoft Agent Framework, LlamaIndex, or any other framework. A second adapter is a new roadmap item, not an extension of this one, and requires the gate below to be met first.
  - Gate: do not start implementation until v1 has a public release and there is real, observed demand — a GitHub issue, integration request, or external contributor asking for it. Architectural hypothesis (deterministic replay is underserved) is not the same as validated demand; this item stays gated on the latter.
  - Definition of done, when ungated: adapter records real trace data from a LangGraph run into Fixtura's existing `.trace` format via LangGraph's native hooks, without modifying LangGraph's own state management; passive replay and OpenEval scoring work against the resulting trace exactly as they do for Fixtura's native tools; acceptance tests 1–6 pass against LangGraph-sourced traces the same as they do for native ones.
- **Counterfactual replay / branching:** 
  - Phase A (Storage schema & TraceReader): ✅ Completed.
  - Phase B (Live execution & security enforcement): ✅ Completed.
- Incident report generation (deterministic format — no fabricated confidence scores)
- Automatic failure classification (Layer 1 infra failures only are automatic; Layer 2–4 require benchmark-defined expected trajectories or manual review)
- Rate limiting / circuit breakers
- Advanced metrics
- **Retrospective / Security Review:** Completed. AGENTS.md autonomous bindings have been officially restricted to read-only operations for v1.1.
- **CI Setup / Symlink Verification:** Completed. GitHub Actions workflow established and path traversal symlink defense natively verified on Linux.
- **Packaging/Distribution:** ✅ Completed. AT5 verified against real PyPI `fixtura==1.0.6`. `permission_reason` spec compliant. OpenEval adapter successfully packaged via `[eval]` extra and CI-verified.

## v2 — Future work, not scoped in detail

- Memory engine (retrieval, forgetting, staleness — a research-scale problem, not a bolt-on)
- Multi-agent coordination
- Cost optimization (needs a real objective function first)
- General-purpose planning engine

## Acceptance tests (v1 is "done" when all six pass — feature count does not matter)

1. **Recording** — ✅ Pass. Record an agent run. Pass if a complete `.trace` artifact is produced.
2. **Replay** — ✅ Pass. Replay the trace. Pass if every recorded step is reproduced without touching any external system (verify: no real DB/API/filesystem calls occur during replay).
3. **Permission enforcement** — ✅ Pass. An unauthorized tool call is blocked *and* still appears in the trace with a "denied" status.
4. **Evaluation harness (AT4)** — ✅ Pass. Predefined benchmark scenarios run through the OpenEval adapter and produce consistent trajectory-level results. (Reproducibility is scoped to trajectory assertions passing consistently, not bit-identical LLM output text — real LLM calls are not deterministic.)
5. **Developer experience** — ✅ Pass. A new developer clones the repo, starts the system, runs a sample recording, replays it, and inspects the trace in under 10 minutes, no exceptions.
6. **Sanitizer verification** — ✅ Pass. Run a scenario where a tool response contains a planted fake secret string. Pass if the persisted `.trace` file does not contain that string. (This validates the one component that exists specifically to fix a stated security gap — do not ship without it.)
