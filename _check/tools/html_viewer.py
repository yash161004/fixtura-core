import argparse
import sys
import json
import html
from pathlib import Path

from recorder.trace_reader import TraceReader, TraceValidationError

def truncate(text: str, max_len: int = 500) -> str:
    if text is None:
        return "None"
    s = str(text)
    if len(s) > max_len:
        return s[:max_len] + f"... [truncated {len(s) - max_len} chars]"
    return s

def generate_html(trace_path: Path) -> str:
    try:
        reader = TraceReader(trace_path)
        events = list(reader.read_events())
    except Exception as e:
        print(f"Error reading trace: {e}")
        sys.exit(1)

    html_parts = [f"""<!DOCTYPE html>
<html>
<head>
    <title>Fixtura Trace Viewer - {html.escape(trace_path.name)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .header {{ margin-bottom: 20px; }}
        .card {{ background: white; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .card-header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 8px; font-weight: bold; }}
        .allowed {{ color: #155724; background-color: #d4edda; padding: 2px 6px; border-radius: 4px; }}
        .denied {{ color: #721c24; background-color: #f8d7da; padding: 2px 6px; border-radius: 4px; }}
        .unknown {{ color: #383d41; background-color: #e2e3e5; padding: 2px 6px; border-radius: 4px; }}
        .label {{ font-weight: bold; font-size: 0.9em; color: #555; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; font-size: 0.9em; margin: 4px 0 12px 0; }}
        .tool-name {{ color: #0056b3; font-family: monospace; font-size: 1.1em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Fixtura Trace Viewer</h2>
            <div>File: <strong>{html.escape(trace_path.name)}</strong></div>
        </div>
"""]

    if not events:
        html_parts.append("<p>No events found in trace.</p>")
    
    for i, event in enumerate(events):
        step_id = event.get("step_id", "?")
        event_type = event.get("event_type", "unknown")
        latency = event.get("latency_ms", "?")
        
        html_parts.append(f"""
        <div class="card">
            <div class="card-header">
                <span>Step {i+1} [{html.escape(step_id)}]</span>
                <span>Type: {html.escape(event_type)} | Latency: {html.escape(str(latency))}ms</span>
            </div>
        """)

        if event_type == "llm_call":
            prompt = event.get("prompt", "")
            completion = event.get("completion", "")
            html_parts.append(f"""
            <div><span class="label">Tool:</span> N/A</div>
            <div><span class="label">Permission:</span> N/A</div>
            <div class="label">Content / Prompt:</div>
            <pre>{html.escape(truncate(str(prompt) if prompt is not None else ""))}</pre>
            <div class="label">Response / Completion:</div>
            <pre>{html.escape(truncate(str(completion) if completion is not None else ""))}</pre>
            """)
        elif event_type == "tool_call":
            tool_name = event.get("tool_name", "unknown")
            decision = event.get("permission_decision", "unknown")
            args_str = json.dumps(event.get("arguments", {}), indent=2)
            
            if decision == "allowed":
                perm_span = f'<span class="allowed">ALLOWED</span>'
                content = event.get("response")
            elif decision == "denied":
                perm_span = f'<span class="denied">DENIED</span>'
                content = event.get("permission_reason")
            else:
                perm_span = f'<span class="unknown">{html.escape(decision)}</span>'
                content = event.get("response")

            html_parts.append(f"""
            <div><span class="label">Tool:</span> <span class="tool-name">{html.escape(tool_name)}</span></div>
            <div><span class="label">Permission:</span> {perm_span}</div>
            <div class="label">Content / Arguments:</div>
            <pre>{html.escape(truncate(str(args_str) if args_str is not None else ""))}</pre>
            <div class="label">Response / Result:</div>
            <pre>{html.escape(truncate(str(content) if content is not None else ""))}</pre>
            """)

        html_parts.append("</div>")

    html_parts.append("""
    </div>
</body>
</html>
""")
    return "".join(html_parts)

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML Viewer for Fixtura .trace files")
    parser.add_argument("trace_file", type=str, help="Path to the .trace file")
    parser.add_argument("-o", "--output", type=str, help="Output HTML file path", default="trace_viewer.html")
    args = parser.parse_args()

    trace_path = Path(args.trace_file)
    if not trace_path.exists():
        print(f"Error: Trace file not found: {trace_path}")
        sys.exit(1)

    html_content = generate_html(trace_path)
    
    out_path = Path(args.output)
    out_path.write_text(html_content, encoding="utf-8")
    print(f"Generated HTML viewer at: {out_path.resolve()}")

if __name__ == "__main__":
    main()
