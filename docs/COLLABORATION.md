# Collaboration model

## Roles

- **Owner (Yashrajsinh)** — final decision-maker. Nothing ships without your approval. You can override any recommendation below.
- **Claude & ChatGPT** — architecture, design review, technical research, and command-writing for Antigravity. Neither writes application code directly in this workflow.
- **Antigravity** — implementation. Takes commands from this repo's docs (primarily `docs/PHASE_*_INSTRUCTIONS.md`) and writes the actual code.

## Working rules for Claude and ChatGPT on this project

1. **Research before recommending.** Before either of us tells you or Antigravity what to build next, we check current best practices, existing tools in the space, and whether something similar already exists — not just reason from training knowledge. (This already changed one decision in this project: the original "AgentOS" pitch was narrowed after research showed the observability-platform space is more crowded than assumed.)
2. **Give one clear recommendation, not a buffet of options**, unless a tradeoff is genuinely close — in which case say so explicitly and explain the fork, rather than listing five options with no stance.
3. **Check `ROADMAP.md` before proposing anything.** If an idea isn't in the frozen v1 table, it goes into "Postponed" — it does not get argued into v1 mid-build. Scope creep during past project attempts is exactly the failure mode this rule exists to prevent.
4. **Every command sent to Antigravity should be concrete and boundaried**: what to build, what the target/definition-of-done is, what NOT to build in this phase, and which acceptance test(s) it must satisfy.
5. **Disagreements between Claude and ChatGPT get surfaced to the owner, not silently resolved.** If we land on different recommendations, both are stated plainly so you make the call.

## How a typical cycle works

1. Owner asks: "What's next?"
2. Claude/ChatGPT check `ROADMAP.md` for the next unbuilt v1 item, research if needed, and produce/update a `docs/PHASE_N_INSTRUCTIONS.md` command doc.
3. Owner reviews and approves (or edits) that doc.
4. Owner feeds it to Antigravity.
5. Antigravity implements; owner or Claude/ChatGPT review the output against the phase's stated acceptance criteria before marking it done.
6. Repeat for the next roadmap item — never skip ahead to a "cooler" idea without updating the roadmap first.
