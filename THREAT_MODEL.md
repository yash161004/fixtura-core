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

**Important Note on Sanitization:** The Sanitizer's pattern-based redaction (Regex Pass 3) is *not* a guaranteed catch-all for arbitrary, unstructured exception text. Structured error formatting at the source (e.g., stripping `input_value` and contexts from Pydantic `ValidationError`s before they reach the recorder) is the primary mitigation. Assuming the Sanitizer alone is sufficient for arbitrary error dumps is a known anti-pattern.

## Explicitly out of scope for v1

- Enterprise-grade DLP (the sanitizer is a stated, simple redact/truncate policy — not a claim of comprehensive data-loss prevention)
- Multi-tenant isolation (single-user/single-session assumption for v1)
- Formal verification of the permission engine (property-based/adversarial testing is a stretch goal, not a v1 commitment)
- Cross-platform native verification of path traversal defenses (specifically: symlink-based escape vectors are skipped on Windows but are now natively verified on Ubuntu CI runners [Run ID: 29064515592, Date: 2026-07-10])

## Phase B (Live Branch) Stated Risks

- **Quota Laundering Gap:** Because each branch is treated as a fresh session, repeated manual branching allows the agent to reset its rate-limiter quota. This gap must be re-evaluated and solved before any multi-tenant or cost-governed deployment.
- **Orphaned Branch Data Loss:** If a parent trace gets deleted (via manual cleanup or retention policy) while a branch still references it via `parent_trace_id`, every dependent branch becomes permanently unreadable. `MissingParentTraceError` handles the read-time symptom correctly, but does not prevent the underlying data loss. This must be solved before retention policy is automated/scheduled.
- **Standing Live Credentials:** Phase B will require standing live credentials wherever it runs, which is a materially different trust boundary than Passive Replay's file-only requirement. Do not let Phase B start without recognizing this shift in the boundary.

Stating these explicitly is intentional — a threat model that claims to solve everything is less credible than one that names its real boundaries.

## Verification requirement

The Sanitizer's redaction claim must be tested, not just implemented. See `ROADMAP.md`, Acceptance Test 6: a tool response containing a planted fake secret must not appear in the persisted trace file.

## Known Testing Gaps

- **Trace Spec Conformance:** Full spec-conformance of trace output isn't currently tested by a comprehensive automated schema assertion. A bug shipped to production in `1.0.2` (where `permission_reason` was null despite `permission_decision` being denied) was only caught by manual inspection of Acceptance Test 5 output. Automated regression tests for trace structural invariants (like `permission_reason` being a non-null string when denied) are required moving forward.
