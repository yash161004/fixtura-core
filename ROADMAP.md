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
| OpenEval Adapter | ✅ Build |
| Trace Viewer UI (minimal) | ✅ Build |
| Threat Model / Architecture / ADRs | ✅ Documentation |
| Test suite | ✅ Build |

## v1.1 — Postponed (do not start until v1 passes all acceptance tests)

- Counterfactual replay / branching
- Incident report generation (deterministic format — no fabricated confidence scores)
- Automatic failure classification (Layer 1 infra failures only are automatic; Layer 2–4 require benchmark-defined expected trajectories or manual review)
- Rate limiting / circuit breakers
- Advanced metrics
- **Retrospective / Security Review:** Completed. AGENTS.md autonomous bindings have been officially restricted to read-only operations for v1.1.

## v2 — Future work, not scoped in detail

- Memory engine (retrieval, forgetting, staleness — a research-scale problem, not a bolt-on)
- Multi-agent coordination
- Cost optimization (needs a real objective function first)
- General-purpose planning engine

## Acceptance tests (v1 is "done" when all six pass — feature count does not matter)

1. **Recording** — Record an agent run. Pass if a complete `.trace` artifact is produced.
2. **Replay** — Replay the trace. Pass if every recorded step is reproduced without touching any external system (verify: no real DB/API/filesystem calls occur during replay).
3. **Permission enforcement** — An unauthorized tool call is blocked *and* still appears in the trace with a "denied" status.
4. **Evaluation harness** — Predefined benchmark scenarios run through the OpenEval adapter and produce consistent trajectory-level results. (Reproducibility is scoped to trajectory assertions passing consistently, not bit-identical LLM output text — real LLM calls are not deterministic.)
5. **Developer experience** — A new developer clones the repo, starts the system, runs a sample recording, replays it, and inspects the trace in under 10 minutes, no exceptions.
6. **Sanitizer verification** — Run a scenario where a tool response contains a planted fake secret string. Pass if the persisted `.trace` file does not contain that string. (This validates the one component that exists specifically to fix a stated security gap — do not ship without it.)
