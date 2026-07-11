# Phase B Notes: Live Branch Execution

- **LiveReplayRuntime**: This module (`replay/live_replay.py`) introduces `LiveReplayRuntime`, which takes a `parent_trace_path`, resolves it up to `divergence_step_id` using `TraceReader`, and serves those events to an `agent_callable`.
- **Pluggable Agent Interface**: To avoid taking heavy LLM dependencies (like `openai` or `anthropic`) in the core library, the runtime accepts an `agent_callable` function. This callable receives the context history and a new prompt, and yields abstract intent dictionaries (`llm_call` and `tool_call_request`).
- **Security Enforcement Loop**: When the agent yields a `tool_call_request`, the runtime intercepts it and routes it through the standard `CapabilityToken` and `RateLimiter` machinery, invoking the underlying `BaseTool`. The results (including `permission_decision` and `rate_limit_decision`) are recorded automatically into the new branch trace.
- **Lineage Resumption**: `ExecutionRecorder` was updated to automatically seed its internal `_step_counter` directly from the numerical suffix of the `divergence_step_id` passed in its constructor. This ensures that branch traces maintain strictly monotonic and unique step IDs without manual manipulation.
- **Dummy CLI Agent**: `cli/branch.py` implements a simple mock agent (similar to `cli/record.py`) to demonstrate and verify the pipeline end-to-end without requiring actual API keys.

## Accepted Technical Debt & Known Gaps (v1.1 Re-evaluation Triggers)
- **Quota Laundering**: As noted in the Threat Model, the `RateLimiter` currently initializes as a fresh session on branch. Resolving this cross-branch quota laundering gap remains an open item for v1.1.
- **Trace Identity/Filename Coupling**: `parent_trace_id` currently relies on `reader.trace_file.stem`. This explicitly couples trace identity to its physical filename, which directly undercuts the `resolve_trace_path` abstraction. A future refactor must assign a real UUID/content-hash trace ID to every trace (independent of filename) and use that for identity. This is accepted debt for v1.0 but must be fixed before multi-backend storage is implemented.
