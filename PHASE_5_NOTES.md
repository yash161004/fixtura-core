# Phase 5 Notes: Trace Viewer UI

## 1. Implementation Summary

The Trace Viewer UI provides a human-readable, visual timeline of an agent's run. While CLI tools output ANSI text, a browser-based UI is far easier to parse, scroll, and copy-paste from when debugging complex AI behaviors.

- **Static HTML Generator (`tools/html_viewer.py`)**: 
  - Parses the `.trace` file using the strictly required `TraceReader`.
  - Outputs a standalone, self-contained `trace_viewer.html` file in the current directory.
  - Formats every step as a dedicated "card" showing step ID, event type, and latency.
  - Implements security by heavily utilizing `html.escape()` on all user/agent inputs to prevent HTML injection/XSS when viewing traces from untrusted sources.
  - Dynamically color-codes permission decisions (Green for `ALLOWED`, Red for `DENIED`) to make security boundaries visually obvious.
- **CLI Subcommand (`cli/html_view.py`)**:
  - Adds the `html-view` subcommand to `fixtura` so users can seamlessly type `fixtura html-view run.trace`.

---

## 2. Phase 5 Architecture Deviations

1. **Static HTML Generation over Live Server**
   - **Deviation**: The viewer does not spin up a local Flask, FastAPI, or Node server. It purely writes a string to an `.html` file.
   - **Reasoning**: Satisfies the v1 criteria for a "minimal" visual timeline without introducing socket management, open ports, or complex asynchronous server code. It keeps the architecture lightweight and immediately accessible.

---

## 3. Known v1 Tradeoffs (By Design)

1. **No Interactive Dashboard Features**
   - **Compromise**: The UI is strictly read-only and linear. There is no search bar, no filtering by tool name, and no sorting by latency.
   - **Reasoning**: Building interactive data-tables requires Javascript frameworks (React/Vue) or heavy vanilla JS. This was explicitly barred from v1 to prevent scope creep.
2. **Local Browser Launch Reliance**
   - **Compromise**: The tool generates the file and (optionally) requests the OS to open it, but relies entirely on the user's local web browser to render it. It does not embed a webview.
