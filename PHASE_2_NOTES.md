# Phase 2 Notes: Execution Recorder & Sanitizer

## Implementation Summary
- **Sanitizer**: The four-pass pipeline is complete. It properly traverses all deeply nested `dict` and `list` structures.
- **Redaction limits**: Truncation calculates sizes dynamically via UTF-8 bytes *post-redaction*, slicing safely with `errors="ignore"` to avoid throwing exceptions on partial multi-byte codepoints before adding `...[TRUNCATED]`.
- **Zstandard Serialization**: The ExecutionRecorder efficiently outputs zstd-compressed JSONL `.trace` files by concatenating frames, safely appending without needing memory-heavy file rewriting.

- **TraceReader (`recorder/trace_reader.py`)**: `TraceReader` is the strictly mandatory and single sanctioned way to read a `.trace` file anywhere in the codebase. It securely decodes multi-frame zstd concatenated streams. Tests, Replay Runtime, Trace Viewer, and OpenEval adapters must strictly import and use `TraceReader.read_events()` and must never interface with `zstandard` directly for trace reading.

## Known v1 Tradeoffs (By Design)

The architecture deliberately accepts two specific compromises for the v1 implementation to adhere to constraints:

1. **Regex False Positives (over-redaction)**
   The deterministic pattern for generic high-entropy strings (`[A-Za-z0-9-_]{40,}`) will inevitably flag and redact non-secret fields like `git commit` hashes, `SHA-256` digests, un-hyphenated UUIDs, and generic session IDs. This reduces debugging fidelity but was chosen over adding heavy machine-learning components (like Presidio/spaCy) for this iteration. This is a known, accepted tradeoff.

2. **No Aggregate Object Size Bound**
   While strings are individually truncated at 50KB (or 20KB for specific `prompt` fields), the sanitizer does not impose an upper limit on the total composite size of an event structure. A pathological tool response consisting of 1,000 separate 49KB strings will bypass the per-string truncation boundary, resulting in a ~50MB event written to the `.trace` artifact. Mitigating runaway agent loop responses or massive structural payloads remains explicitly out of scope for v1 as stated in `THREAT_MODEL.md`.
