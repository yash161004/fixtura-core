# Phase 4 Notes: OpenEval Adapter

## 1. Implementation Summary

The OpenEval Adapter bridges the gap between Fixtura's native `.trace` recording format and the third-party OpenEval grading engine. Its purpose is to grade an agent's execution without needing a live environment.

- **Adapter (`tools/openeval_adapter.py`)**: 
  - Iterates over all events parsed by `TraceReader`.
  - Translates Fixtura's `tool_call` and `llm_call` structures into the canonical `AgentTrace` object schema expected by OpenEval.
  - Correctly maps Fixtura's `latency_ms` and tool arguments into the required dictionary shapes.
- **Evaluation CLI (`cli/eval.py`)**:
  - Initializes OpenEval's core metrics: `ToolSelectionAccuracy`, `ArgumentCorrectness`, `StepEfficiency`, and `GoalCompletionRate`.
  - Executes the metric calculation synchronously against the extracted `AgentTrace`.
  - Outputs the results via `pprint` for immediate developer feedback.

---

## 2. Phase 4 Architecture Deviations

1. **Fixed Canonical Task (No Dynamic Suites)**
   - **Deviation**: Instead of implementing a dynamic benchmark loader that parses JSON/YAML suites of thousands of test cases, the implementation relies on a single, hardcoded `EvalTestCase`.
   - **Reasoning**: Satisfies the v1 requirement to prove the adapter works end-to-end without getting bogged down in file-parsing edge cases for various benchmark datasets (e.g., WebArena, GAIA).

---

## 3. Known v1 Tradeoffs (By Design)

1. **Trajectory-Level Assertions Only (No Text Matching)**
   - **Compromise**: The adapter strictly verifies deterministic actions: Did the agent pick the correct tool? Did it supply the correct JSON arguments?
   - **Reasoning**: We explicitly ignore the actual text completion output (the non-deterministic LLM string) for scoring. LLMs vary wildly in how they say "I finished the task", so reproducible evaluation requires focusing strictly on the functional API calls (the trajectory).

2. **No Multi-Trace Batch Orchestration**
   - **Compromise**: The CLI evaluates exactly one trace at a time.
   - **Reasoning**: Batch processing, parallel evaluation, and aggregate dashboards are deferred to later versions. The focus of v1 is successfully evaluating a single recorded artifact.
