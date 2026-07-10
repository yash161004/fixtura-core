# Threat Model

## Trust boundaries

```
[ Untrusted: LLM output / agent decisions ]
              │
              ▼
[ Trust boundary: Permission Engine ] ← every tool call crosses this
              │
              ▼
[ Trusted: Tool Executor → real filesystem / DB / API ]
              │
              ▼
[ Trust boundary: Sanitizer ] ← every recorded event crosses this
              │
              ▼
[ Persisted: .trace storage ]
```

The core assumption: **LLM-generated tool call arguments are untrusted input**, exactly like any other user-supplied input to a backend system. They must be validated against a schema before touching a real tool, never interpolated directly into shell commands, SQL, or file paths.

## Assets

- Filesystem / database / API credentials the agent has access to
- `.trace` recordings (may contain secrets, PII, or proprietary data that flowed through tool calls)
- The permission policy itself (if tampered with, everything downstream is compromised)

## Threats and mitigations (v1 scope)

| Threat | Mitigation |
|---|---|
| Agent-supplied arguments used unsafely (injection) | Schema validation on every tool call before execution; no raw string interpolation into shell/SQL/paths |
| Unauthorized tool invocation (agent does something it shouldn't) | Permission Engine checks every call against a capability-scoped token; denials are still recorded, not silently dropped |
| Secrets/PII leaking into persisted trace files | Sanitizer redact/truncate policy runs before any write to storage (see ARCHITECTURE.md) |
| Replay accidentally executing real side effects (double-write, duplicate API call) | Replay Runtime never invokes the real Tool Executor — every LLM completion and tool response is substituted from the recording, full stop |
| Runaway agent loop hammering a real tool | Cross-cutting rate limiter per-session and per-time-window, plus consecutive-failure circuit breaker to abort tool usage automatically. |

## Explicitly out of scope for v1

- Enterprise-grade DLP (the sanitizer is a stated, simple redact/truncate policy — not a claim of comprehensive data-loss prevention)
- Multi-tenant isolation (single-user/single-session assumption for v1)
- Formal verification of the permission engine (property-based/adversarial testing is a stretch goal, not a v1 commitment)
- Cross-platform native verification of path traversal defenses (specifically: symlink-based escape vectors are skipped on Windows but are now natively verified on Ubuntu CI runners [Run ID: 29064515592, Date: 2026-07-10])

Stating these explicitly is intentional — a threat model that claims to solve everything is less credible than one that names its real boundaries.

## Verification requirement

The Sanitizer's redaction claim must be tested, not just implemented. See `ROADMAP.md`, Acceptance Test 6: a tool response containing a planted fake secret must not appear in the persisted trace file.
