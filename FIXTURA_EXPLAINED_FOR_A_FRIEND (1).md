# Fixtura — The Whole Story, Explained Simply

*For: the friend implementing Phases 4-6. Written to be read start to finish, no prior context assumed.*

---

## 1. What problem this is solving

When you build an AI agent (something that uses an LLM to decide what tool to call — read a file, hit an API, query a database), testing it is a mess. Every time you run it, the LLM might answer slightly differently, the agent might call things in a different order, and if it's hitting real APIs or a real database, every test run has side effects — real emails sent, real rows written, real money spent on API calls.

Existing tools that watch what an agent does (Langfuse, Phoenix, Braintrust, Laminar) are built for **production monitoring at scale** — dashboards, alerting, watching agents in the wild. That's not what this project is for.

**Fixtura's idea:** record one real run of an agent exactly once — every tool call, every LLM response, every decision — then let you **replay that exact recording offline, forever, with zero live calls**, the same way a snapshot test lets a UI test re-check a rendered component without re-rendering the whole app from scratch. You can then use that recording to debug a failure after the fact, or run it in CI to catch regressions, the same way a unit test gates a pull request.

It's built to hand its recordings to **OpenEval** — a separate tool, already built, that scores whether an agent's behavior was good (picked the right tool, got the arguments right, was efficient, actually completed the goal). Fixtura doesn't grade anything itself. It produces the raw material; OpenEval does the grading.

---

## 2. What kind of thing this actually is (not an app, not a framework)

If you're picturing a website or a dashboard: wrong picture. [Certain]

- **It's not a framework** like OpenEval — it doesn't define what "correct agent behavior" means, and it doesn't run evaluations itself.
- **It's not a consumer-facing app** — there's no marketing site, no accounts, no multi-user dashboard planned for v1.
- **It's closest to a developer library**, like `pytest` (a testing tool) combined with something like VCR.py (a "record a real HTTP call once, replay it forever in tests" tool), plus a small internal viewer window so a developer can look at what got recorded without reading raw JSON.

The one piece that looks like "UI" — the Trace Viewer — is explicitly designed to be as small as possible. It answers exactly five questions (what happened, in what order, which tool, how long, was it allowed) and nothing more. No filtering, no search, no dashboard. This was a deliberate decision, written down early, specifically because that kind of feature tends to balloon if nobody stops it.

---

## 3. Why it started this way (the design history)

Early on, there was a much bigger pitch on the table — a six-part "AgentOS" idea that included a planning engine, a memory engine, a cost optimizer, multi-agent communication, and a tool selector, on top of the recording/replay idea. All of that got cut before any code was written, for concrete reasons:

- **Tool Selector** — not useful yet; the LLM already picks between 4-5 tools fine on its own at this scale.
- **Memory Engine** — retrieval/ranking/forgetting is its own hard research problem, not something you bolt on.
- **Cost Optimizer** — without a clear goal to optimize for, it's just guessing.
- **Multi-agent Communication** — doesn't help the actual debugging problem this project exists to solve.

That cut was made *after* checking what already existed in the market (that's when it became clear the observability-tool space was already crowded — Langfuse, Phoenix, Braintrust, Laminar all exist), which is why the project narrowed to something specific: **recorded traces as literal, replayable test fixtures** — a gap those bigger tools don't really target, since they're built for live production monitoring, not offline regression testing.

Once the scope was cut, it got **frozen in writing** (`ROADMAP.md`) specifically because earlier design conversations kept re-adding scope after agreeing to remove it. The rule since then: nothing gets built that isn't in that frozen table, full stop, until all six "is v1 done" tests pass.

---

## 4. How the team works (so you know what to expect)

Four roles:

- **Owner (Yashrajsinh)** — makes every final call. Nothing ships without sign-off.
- **Claude & ChatGPT** — do architecture review and write precise build instructions. Neither writes the actual application code.
- **Antigravity** — the AI coding agent that actually implements things, working strictly from written phase instructions.
- **You** — implementing the two phases still left.

The review process has one hard rule that's been enforced strictly every phase so far: **nothing counts as "done" from a description.** Every claim of "tests pass" gets backed by pasting the actual, unabridged test output and often the actual source code — not a summary of it. This caught real bugs at every single phase. Whoever reviews your work needs to keep applying this same standard, or bugs that would've been caught early will slip through instead.

---

## 5. Phase by phase: what's been built, in plain terms

### ✅ Phase 1 — Tool Execution Layer + Permission Engine (DONE)

**In plain terms:** built three basic tools the agent can use — read/write files (only inside a safe folder), read/write a local database, and make web requests (only to an approved list of websites). Then built a gatekeeper (the Permission Engine) that every single tool call has to pass through — it checks "is this agent actually allowed to do this?" before anything runs for real. If the agent tries something outside its allowed scope (like writing outside its sandbox folder, or hitting a random website), it gets blocked.

**Why this came first:** everything else in the project watches or records tool calls. If the tools and the permission checks aren't solid, everything built on top of them is just faithfully recording a broken foundation.

**Key detail:** the permission check lives in exactly one place in the code — no individual tool is allowed to do its own permission logic. That was a deliberate design rule to prevent security checks from getting duplicated (and inconsistently done) across every tool.

### ✅ Phase 2 — Execution Recorder + Sanitizer (DONE)

**In plain terms:** built the part that actually writes down everything that happens — every tool call, every LLM response, whether it was allowed or denied — into a file (a `.trace` file). But before anything gets written to disk, it passes through a **Sanitizer**: a filter that strips out anything that looks like a password, API key, or secret token, and trims anything too large.

**Why this matters:** "record everything the agent does" is dangerous by itself — agents often have secrets flowing through their tool calls (API keys, tokens). If Fixtura just recorded raw data, it would be creating a pile of leaked secrets sitting on disk. The Sanitizer exists specifically to prevent that.

**This was tested directly**, not assumed: a fake secret string was deliberately planted in a tool response, and the recorded file was checked afterward to confirm that string never appears in it. It didn't.

### ✅ Phase 3 — Replay Runtime (DONE — most recently finished, and the most heavily reviewed)

**In plain terms:** this is the "replay" half of "record and replay." Two modes:

- **Passive Replay** — takes a `.trace` file and plays the whole run back exactly as it happened, substituting in the recorded responses instead of actually calling anything live. No real API calls, no real database writes, nothing — it's a pure playback.
- **Step Inspection** — same idea, but it pauses after every single step so a developer can look at exactly what happened (what was asked, what came back, was it allowed, how long did it take) before manually continuing to the next step. Strictly look-only — no editing, no re-running with different inputs, no "what if" branching. That kind of thing (branching/what-if replay) was deliberately postponed to a later version, not built now.

**This phase went through the most scrutiny of any phase so far.** Four real bugs were caught by insisting on seeing actual code and actual test output instead of trusting descriptions:
1. A missing check meant a corrupted trace file with a garbage value in a critical field would silently pass validation instead of being rejected.
2. A required timestamp field wasn't actually being checked for.
3. The replay code originally couldn't tell the difference between "this tool call was blocked/denied" and "this tool call succeeded but returned nothing" — both showed up as the same blank result, which would have made it impossible to trust the replayed history.
4. A type-checking detail was left inaccurate after a fix (labeled as "could return anything" when it actually only ever returned one specific shape of data).

All four got fixed and re-verified with real pasted output before this phase was signed off.

### ❌ Phase 4 — OpenEval Adapter (NOT STARTED — this is one of your two phases)

**In plain terms:** a translator. It takes a `.trace` file and converts it into the exact format OpenEval expects (`AgentTrace`), so OpenEval's existing scoring tools (did the agent pick the right tool? were the arguments correct? was it efficient? did it actually finish the goal?) can run against a *real recorded agent run* instead of a live one.

**The one blocker before this can be fully specified:** nobody has looked at OpenEval's actual `AgentTrace` schema yet. That has to happen first — guessing the field names/shapes and hoping they match is exactly the kind of silent failure this project has caught repeatedly elsewhere (bad data goes in, a plausible-looking score comes out, nothing errors, nobody notices until much later).

**What "done" looks like:** a real recorded trace gets converted and actually scored by OpenEval's real metric functions (not fake/mocked ones), and a deliberately-broken test trace (with a known permission denial and a known bad argument) gets correctly reflected in the score rather than silently dropped.

### ❌ Phase 5 — Trace Viewer UI (NOT STARTED — your other phase)

**In plain terms:** the small window/interface a developer opens to actually look at a `.trace` file without reading raw JSON — shows the sequence of events, which tool, how long each step took, whether it was allowed, and the recorded data for each step.

**The trap to watch for:** every well-known example of a "trace viewer" in this space (Langfuse, Phoenix, etc.) comes with filtering, search, comparison across multiple runs, dashboards. **None of that is in scope here.** If you look up "best practice trace viewer" for inspiration, you'll find tools a full tier more complex than what this phase is asking for. Stick to the five questions listed in section 2 above, nothing more.

### 🟡 Phase 6 — Integration / End-to-End Pass (NOT FORMALLY STARTED, WILL BE NEEDED)

**In plain terms:** once Phases 4 and 5 exist, someone needs to run the *entire* pipeline start to finish — clone the repo, run a real agent, get a trace, replay it, step through it, view it, score it with OpenEval — and time the whole thing. This hasn't happened yet because the pieces it depends on don't exist yet. Individually-correct pieces can still fail to fit together (a file path assumption that's wrong, a format mismatch between what one phase writes and the next expects) — this phase exists to catch exactly that.

---

## 6. Current status, summarized

**4 of 6 "is v1 done" tests pass. 2 remain, and both are blocked on Phases 4-6, which haven't started.**

| # | Test | Status |
|---|---|---|
| 1 | Recording produces a complete trace file | ✅ Pass |
| 2 | Replay reproduces every step with zero live calls | ✅ Pass |
| 3 | A blocked tool call is denied *and* still shows up in the trace | ✅ Pass |
| 4 | OpenEval adapter produces consistent scoring | ❌ Not buildable yet |
| 5 | A new developer can clone, record, replay, and inspect a trace in under 10 minutes | ❌ Not testable yet — no viewer, no full walkthrough done |
| 6 | A planted fake secret never ends up in a saved trace file | ✅ Pass (tested directly) |

The hard, security-relevant engineering (permission boundaries, secret redaction, replay fidelity) is done and has held up under repeated scrutiny. What's left is more mechanical, but Phase 4 specifically has one real unknown (OpenEval's actual schema) that needs research before it can be precisely specified.

---

## 7. Does anyone actually get to use this? [Certain]

Not yet, and not soon, by deliberate choice, not accident:

- The GitHub repo is **private** — only invited people can see or use it.
- **No license has been chosen** — for a private repo this doesn't matter yet, but it means it legally can't be shared or reused by anyone outside the project as-is.
- **v1 isn't finished** — 2 of 8 components don't exist, 2 of 6 correctness tests are unproven.

For a real outside user to use this, at minimum: v1 has to ship, a license has to be picked, and the repo would need to go public (or be shared privately with specific people first, which is the more sensible next step — a small private beta before any public release).

---

## 8. Can this become a business? [Likely — direct opinion, not hedged]

Not yet, and the honest reason isn't "the idea is bad" — it's that **the project hasn't reached the point where that question is even answerable.** Business viability gets decided by strangers actually using the thing and choosing to pay for it or not. Right now:

- Zero people outside this two-person project have touched it.
- The market it's aimed at (developer tooling for AI agents) is already crowded — Langfuse, Phoenix, Braintrust, and Laminar all exist and are well-funded. Fixtura's angle (offline recorded fixtures for regression testing, not live production monitoring) is a real, specific gap in that space — but "there's a gap" isn't the same as "people will pay to fill it with this."
- No one has validated that developers actually want *offline replay as a testing pattern* for agents specifically, versus just using the production-monitoring tools that already exist and calling it good enough.

**What would actually need to happen before "can we start a business" is a real question, not a hopeful one:**
1. Finish v1 (Phases 4-6).
2. Get 5-10 real outside developers to actually use it on their own agents — not you two testing your own tool.
3. See if any of them would pay for it, or if they'd rather just use Langfuse/Phoenix and not think about it further.
4. Only after that: license, positioning, pricing, go-to-market — the actual business questions.

Skipping to step 4 before step 2 is a common way good engineering projects turn into unused products. Finish the build, get real hands on it, then revisit this.

---

## 9. What "done" (v1 shipped) actually looks like, end to end

A developer clones the repo and, in one sitting:

1. Runs a real agent against Fixtura's three tools (file access, database, web requests) — every call checked against a permission scope before it's allowed to happen.
2. Gets a `.trace` file out — compressed, with every secret redacted before it ever touches disk.
3. Replays it with zero live calls — sees the exact same run happen again, including any blocked/denied calls, exactly as they occurred the first time.
4. Steps through it one event at a time in a small viewer, seeing what happened, what tool, how long, was it allowed.
5. Runs it through the OpenEval adapter and gets a real score: did the agent pick the right tool, get the arguments right, work efficiently, actually finish the job.

That's the whole idea, concretely: **a real agent run becomes a reusable, offline, gradeable test** — the same way a snapshot test lets a UI regression get caught automatically instead of a human staring at a screenshot. Nothing more than that in v1 — no "what if" branching replays, no auto-generated incident reports, no multi-agent anything. Those are named and deliberately postponed, not forgotten.
