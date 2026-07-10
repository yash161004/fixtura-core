# Collaboration & Review Discipline

4. **Task Definitions:** Every Antigravity command must state what to build and what "done" looks like.
5. **Evidence standard for phase sign-off:** No phase is marked done on a summary, a manual CLI demonstration, or a self-reported "tests pass." Sign-off requires pasted, unabridged `pytest -v` and `mypy --strict` output showing the actual run, plus explicit pass/fail mapping to the relevant acceptance test(s) in ROADMAP.md. If a test is skipped, the skip reason and platform must be stated, and the skip must be tracked as an open item until resolved on a representative environment (not silently accepted as equivalent to a pass).
