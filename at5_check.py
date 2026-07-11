import asyncio
import os
import json
from recorder.recorder import ExecutionRecorder
from security.permission_engine import CapabilityToken, check

def main() -> None:
    trace_path = "at5_final.trace"
    if os.path.exists(trace_path):
        os.remove(trace_path)
    
    recorder = ExecutionRecorder(trace_path)
    token = CapabilityToken()
    token.http.allowed_domains = ["api.github.com"]

    tool_name = "http_tool"
    # missing method
    tool_args = {"url": "not-a-url"}
    allowed, reason = check(token, tool_name, tool_args)

    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 2001.0,
        "tool_name": tool_name,
        "arguments": tool_args,
        "permission_decision": "denied" if allowed == "permission_denied" else "allowed",
        "permission_reason": reason,
        "response": None,
        "latency_ms": 50
    })

    from recorder.trace_reader import TraceReader
    reader = TraceReader(trace_path)
    for event in reader.read_events():
        if event.get("event_type") == "tool_call" and event.get("permission_decision") == "denied":
            print("\nRAW EVENT FROM TRACE:")
            print(json.dumps(event, indent=2))
            print("\npermission_reason field:")
            print(event.get("permission_reason"))

if __name__ == "__main__":
    main()
