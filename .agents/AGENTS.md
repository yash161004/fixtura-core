# Fixtura Agent Rules

## Trigger Condition
**Re-evaluate these rules when:**
- A new major Phase (e.g., Phase 2) begins.
- Introducing new state-mutating functionality or new MCP integrations.
- GitHub deprecates an action version currently in use (e.g., Node 20 phase-out requires bumping actions).

---

The following rules apply to all tasks executed in this workspace:

1. **MCP Usage Policy:**
   - **Read-only bindings** (e.g., Context7 documentation lookups, SQLite SELECT queries, reading files) MUST be executed autonomously to maintain velocity. Do not stop to ask for permission.
   - **State-mutating bindings** (e.g., raw SQLite INSERT/DROP/UPDATE, GitHub issue/PR creation, posting to Slack, automated refactoring tools) MUST require explicit user confirmation before execution. You may propose the command/tool call, but stop and wait for the user to approve.
