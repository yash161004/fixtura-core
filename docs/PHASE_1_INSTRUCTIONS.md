# Phase 1 Instructions

**Read `ARCHITECTURE.md`, `THREAT_MODEL.md`, and `TRACE_FORMAT_SPEC.md` before starting. This document is the command; those are the design contract.**

## Target for this phase

Build the **Tool Execution Layer** and **Permission Engine** only. Nothing else. Do not start the Recorder, Replay, Trace Viewer, or OpenEval adapter in this phase — they depend on this phase being correct first.

## Why this order

Every other component wraps around tool calls. If the execution layer and permission engine aren't solid, the recorder will faithfully record a broken system. Build the foundation first.

## Concrete deliverables

1. **3 tools**, each in its own module under `tools/`:
   - `filesystem_tool.py` — read/write within a configurable sandboxed root directory only (never outside it)
   - `sqlite_tool.py` — query/write against a local SQLite DB (Postgres comes in a later phase)
   - `http_tool.py` — GET/POST to an allow-listed set of domains only

   Each tool must:
   - Declare an input schema (use `pydantic`) and validate arguments before execution
   - Declare `is_idempotent: bool` and `is_reversible: bool` as metadata
   - Never interpolate raw arguments into file paths, SQL, or shell commands — use parameterized queries and path-joining that rejects `../` traversal

2. **Permission Engine**, in `security/permission_engine.py`:
   - A `CapabilityToken` object scoping what a session may do (e.g., `{"filesystem": {"read": ["/workspace"], "write": []}, "db": {"read": true, "write": false}, "http": {"allowed_domains": [...]}}`)
   - A single `check(session_token, tool_name, arguments) -> (allowed: bool, reason: str)` function that every tool call must pass through before execution — no tool may check permissions itself
   - Denials must return a clear reason string (this will be recorded once the Recorder phase exists)

3. **Tests** (`pytest`), minimum:
   - Each tool's schema validation rejects malformed input
   - Path traversal attempt (`../../etc/passwd`) is rejected by the filesystem tool
   - SQL injection attempt is neutralized (parameterized query, not string interpolation)
   - Permission Engine denies an out-of-scope filesystem write and allows an in-scope one
   - Permission Engine denies an HTTP call to a non-allow-listed domain

## Definition of done

- All Phase 1 tests pass
- No tool contains a direct permission check inline (permission logic lives only in `security/permission_engine.py`)
- Code is typed (type hints throughout, pass `mypy` or `pyright` in strict-ish mode)
- A short `PHASE_1_NOTES.md` is written documenting any deviation from this spec and why

## Explicitly not in scope for this phase

- Recorder/Sanitizer, Replay, Trace Viewer, OpenEval adapter, Docker/CI setup, Postgres migration
- Rate limiting, retries, circuit breakers (v1.1)

## Tech stack for this phase

Python 3.11+, `pydantic` for schemas, `pytest` for tests. No web framework needed yet — this phase is pure library code, callable directly, no HTTP server required until a later phase wires it up.


## Addendum (pre-implementation fixes, same phase/scope — no new features)

- Filesystem tool: sandbox check must use resolved/real paths (resolve symlinks) and verify
  the resolved path is a descendant of the sandbox root — not a string-match on `../`.
- HTTP tool: disable automatic redirect-following (or re-validate the domain allow-list on
  every redirect hop). Resolve the domain to an IP before connecting and reject
  private/loopback/link-local ranges (e.g. 127.0.0.0/8, 169.254.0.0/16, 10.0.0.0/8,
  172.16.0.0/12, 192.168.0.0/16).
- Permission Engine order: schema validation (pydantic) runs first; `check()` runs on
  validated arguments. Tool call results must be one of three distinguishable outcomes:
  `validation_error`, `permission_denied`, or `executed` — not a single boolean.
- SQLite tool: DB file path must be configurable and scoped the same way the filesystem
  tool's root is (no arbitrary DB path from agent input). The read/write permission model
  is table-agnostic in v1 (CapabilityToken's `db: {read, write}` is global, not per-table) —
  state this explicitly in PHASE_1_NOTES.md as a known v1 simplification, not an oversight.
- Naming: use `CapabilityToken` consistently as both the object name and the parameter name
  in `check(capability_token, tool_name, arguments)`.