# Fixtura Agent Rules

The following rules apply to all tasks executed in this workspace:

1. **MCP Usage Policy:**
   - **Read-only bindings** (e.g., Context7 documentation lookups, SQLite SELECT queries, reading files) MUST be executed autonomously to maintain velocity. Do not stop to ask for permission.
   - **State-mutating bindings** (e.g., raw SQLite INSERT/DROP/UPDATE, GitHub issue/PR creation, posting to Slack, automated refactoring tools) MUST require explicit user confirmation before execution. You may propose the command/tool call, but stop and wait for the user to approve.
