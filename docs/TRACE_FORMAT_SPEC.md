# Trace Format Spec

Every `.trace` file is JSONL (one JSON object per line), one line per event. This format must be convertible to OpenEval's `AgentTrace` object via the adapter in `docs/PHASE_1_INSTRUCTIONS.md`'s later phases — treat this as the contract between Fixtura and OpenEval.

## LLM step event

```json
{
  "event_type": "llm_call",
  "step_id": "string, unique within run",
  "timestamp": "ISO 8601",
  "prompt": "string (sanitized)",
  "completion": "string (sanitized)",
  "provider": "string",
  "model": "string",
  "temperature": "number | null",
  "top_p": "number | null",
  "input_tokens": "int",
  "output_tokens": "int",
  "finish_reason": "string",
  "latency_ms": "int"
}
```

## Tool call event

```json
{
  "event_type": "tool_call",
  "step_id": "string, unique within run",
  "timestamp": "ISO 8601",
  "tool_name": "string",
  "arguments": "object (sanitized)",
  "validated_arguments": "object (post-schema-validation, only if different from arguments)",
  "permission_decision": "allowed | denied",
  "permission_reason": "string, required if denied",
  "rate_limit_decision": "allowed | rate_limited | circuit_broken (optional)",
  "rate_limit_reason": "string, required if rejected (optional)",
  "response": "object | null (sanitized, null if denied)",
  "exception": "string | null",
  "latency_ms": "int"
}
```

## Sanitization contract

No event may be written to disk before passing through the Sanitizer described in `ARCHITECTURE.md`. Fields under `redact` are replaced with `"[REDACTED]"`; fields under `truncate` are cut to the stated limit with a `"...[TRUNCATED]"` marker. This is non-negotiable per `THREAT_MODEL.md` — do not add a code path that writes directly to the trace file bypassing the sanitizer.

Note: `rate_limit_decision` and `rate_limit_reason` were introduced in v1.1. They are optional for backwards compatibility but explain why a call was rejected independently of the permission engine.

## Determinism requirement

Passive Replay must be able to reconstruct a full run using **only** the fields above — no live calls to any LLM provider or external tool during replay. If a field needed for faithful replay is missing from this spec, add it here before implementing, don't add it silently in code.
