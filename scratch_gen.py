import os
import sys
sys.path.append(r"c:\Users\pmb13\Downloads\fixtura\fixtura")
from recorder.recorder import ExecutionRecorder

def generate_mixed_trace(trace_path: str) -> None:
    if os.path.exists(trace_path):
        os.remove(trace_path)
    recorder = ExecutionRecorder(trace_path)
    
    recorder.record_event({
        "event_type": "llm_call",
        "timestamp": 1000.0,
        "prompt": "You are a helpful assistant.",
        "completion": "I will read the file.",
        "provider": "openai",
        "model": "gpt-4",
        "input_tokens": 10,
        "output_tokens": 20,
        "finish_reason": "stop",
        "latency_ms": 500
    })
    
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 1001.0,
        "tool_name": "filesystem_tool",
        "arguments": {"operation": "read", "path": "test.txt"},
        "permission_decision": "allowed",
        "response": "File contents here",
        "latency_ms": 100
    })
    
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 2001.0,
        "tool_name": "filesystem_tool",
        "arguments": {"operation": "read", "path": "critical.sys"},
        "permission_decision": "denied",
        "permission_reason": "Not allowed to read sys files",
        "response": None,
        "latency_ms": 50
    })

if __name__ == "__main__":
    generate_mixed_trace("mixed.trace")
