# Collaboration model

## Roles

- **Yashrajsinh Rathod** — owner. Final decision-maker on scope, architecture, and releases.
- **Meet Patel** — owner. Full standing alongside Yashrajsinh on scope, architecture, and releases.

Either owner can approve or override a decision; genuine disagreements between the two get talked through directly rather than one silently deferring.

## Working rules on this project

1. **Research before recommending.** Before committing to what gets built next, check current best practices and existing tools in the space — not just reason from assumption. (This already changed one decision in this project: the original "AgentOS" pitch was narrowed after research showed the observability-platform space is more crowded than assumed.)
2. **Give one clear recommendation, not a buffet of options**, unless a tradeoff is genuinely close — in which case say so explicitly and explain the fork, rather than listing five options with no stance.
3. **Check `ROADMAP.md` before proposing anything.** If an idea isn't in the frozen v1 table, it goes into "Postponed" — it does not get argued into v1 mid-build. Scope creep during past project attempts is exactly the failure mode this rule exists to prevent.
4. **Every implementation task should be concrete and boundaried**: what to build, what the target/definition-of-done is, what NOT to build in this phase, and which acceptance test(s) it must satisfy.
5. **Nothing is marked done on a summary or a self-reported "tests pass."** Sign-off requires pasted, unabridged `pytest -v` and `mypy --strict` output, mapped explicitly to the relevant acceptance test(s) in `ROADMAP.md`.

## How a typical cycle works

1. Check `ROADMAP.md` for the next unbuilt v1 (or approved v1.1) item.
2. Write or update a `docs/PHASE_N_INSTRUCTIONS.md` command doc: what to build, definition of done, explicit non-goals, which acceptance test(s) it satisfies.
3. Both owners review and approve (or edit) that doc before implementation starts.
4. Implement against the approved doc.
5. Review the output against the phase's stated acceptance criteria — real test output, verified CI run — before marking it done.
6. Repeat for the next roadmap item — never skip ahead to a different idea without updating the roadmap first.
