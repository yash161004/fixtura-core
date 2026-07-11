# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-07-10
### Fixed
- Working release. Fixed packaging issues.

## [1.0.1] - 2026-07-10
### Notes
- TestPyPI-only release to verify packaging fixes.

## [1.0.0] - 2026-07-10
### Notes
- [BROKEN] First release, broken on install.

### Added
- **Tool Execution Layer:** A deterministic execution environment supporting Filesystem, SQLite, and HTTP capabilities.
- **Permission Engine:** Cross-cutting capability token enforcement to sandbox agent executions (e.g., preventing directory traversal, path escapes, SQL injections, and SSRF attacks).
- **Execution Recorder & Sanitizer:** Zstandard-compressed trace logging with streaming redaction of sensitive credentials and PII.
- **Passive Replay & Step Inspection:** Deterministic offline replay of traces to validate agent behavior without invoking live systems.
- **Trace Viewer UI:** A lightweight UI for visualizing agent traces.
- **OpenEval Adapter:** Transformation logic to map Fixtura traces into OpenEval's AgentTrace format for evaluation.
- **Rate Limiting & Circuit Breakers:** Cross-cutting protections against runaway agent loops (added as part of v1.1 scope, included in this initial release).

### Notes
- **Acceptance Test 4 Caveat:** The OpenEval evaluation harness (Acceptance Test 4) relies on the OpenEval package which is not yet published to PyPI. As such, a standard pip install fixtura will **not** include the OpenEval dependency. Attempting to use the openeval_adapter without a manual Git install of OpenEval will raise a graceful RuntimeError. See the README for manual installation instructions.
