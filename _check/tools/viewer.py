import argparse
import sys
import json
from pathlib import Path

from recorder.trace_reader import TraceReader, TraceValidationError

# ANSI Colors
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
DIM = "\033[2m"

def truncate(text: str, max_len: int = 500) -> str:
    if text is None:
        return "None"
    s = str(text)
    if len(s) > max_len:
        return s[:max_len] + f"... {DIM}[truncated {len(s) - max_len} chars]{RESET}"
    return s

def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal Trace Viewer for Fixtura .trace files")
    parser.add_argument("trace_file", type=str, help="Path to the .trace file")
    args = parser.parse_args()

    trace_path = Path(args.trace_file)
    if not trace_path.exists():
        print(f"{RED}Error: Trace file not found: {trace_path}{RESET}")
        sys.exit(1)

    try:
        reader = TraceReader(trace_path)
    except Exception as e:
        print(f"{RED}Error initializing TraceReader: {e}{RESET}")
        sys.exit(1)

    print(f"{BOLD}--- FIXTURA TRACE VIEWER ---{RESET}")
    print(f"{DIM}File: {trace_path.name}{RESET}")
    print("=" * 80)

    try:
        events = list(reader.read_events())
    except TraceValidationError as e:
        print(f"{RED}Trace Validation Error: {e}{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}Failed to read trace events: {e}{RESET}")
        sys.exit(1)

    if not events:
        print("No events found in trace.")
        sys.exit(0)

    for i, event in enumerate(events):
        step_id = event.get("step_id", "?")
        event_type = event.get("event_type", "unknown")
        latency = event.get("latency_ms", "?")
        
        # Format the header
        header = f"{BOLD}Step {i+1} [{step_id}]{RESET} | Type: {CYAN}{event_type}{RESET} | Latency: {latency}ms"
        print(header)

        # Print type-specific details
        if event_type == "llm_call":
            print(f"  {DIM}Tool: N/A{RESET}")
            print(f"  {DIM}Permission: N/A{RESET}")
            
            prompt = event.get("prompt", "")
            completion = event.get("completion", "")
            
            print(f"  {BOLD}Content / Prompt:{RESET}")
            print(f"    {truncate(str(prompt) if prompt is not None else '')}")
            print(f"  {BOLD}Response / Completion:{RESET}")
            print(f"    {truncate(str(completion) if completion is not None else '')}")

        elif event_type == "tool_call":
            tool_name = event.get("tool_name", "unknown")
            decision = event.get("permission_decision", "unknown")
            args_str = json.dumps(event.get("arguments", {}))
            
            print(f"  {BOLD}Tool:{RESET} {YELLOW}{tool_name}{RESET}")
            
            if decision == "allowed":
                print(f"  {BOLD}Permission:{RESET} {GREEN}ALLOWED{RESET}")
                content = event.get("response")
            elif decision == "denied":
                print(f"  {BOLD}Permission:{RESET} {RED}DENIED{RESET}")
                content = event.get("permission_reason")
            else:
                print(f"  {BOLD}Permission:{RESET} {decision}")
                content = event.get("response")
                
            print(f"  {BOLD}Content / Arguments:{RESET}")
            print(f"    {truncate(str(args_str) if args_str is not None else '')}")
            print(f"  {BOLD}Response / Result:{RESET}")
            print(f"    {truncate(str(content) if content is not None else '')}")

        print("-" * 80)

if __name__ == "__main__":
    main()
