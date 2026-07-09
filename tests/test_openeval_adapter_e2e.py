import os
import json
from pathlib import Path
from pprint import pprint

from tools.openeval_adapter import trace_to_agent_trace
from recorder.recorder import ExecutionRecorder
from openeval.runner import run_eval
from openeval.models import EvalTestCase
from openeval.metrics import ToolSelectionAccuracy, ArgumentCorrectness, StepEfficiency, GoalCompletionRate
from security.permission_engine import CapabilityToken, check

def generate_simple_trace(trace_path: str):
    if os.path.exists(trace_path):
        os.remove(trace_path)
    recorder = ExecutionRecorder(trace_path)
    
    # 1. Thought/llm_call
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
    
    # 2. Tool call (allowed)
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 1001.0,
        "tool_name": "filesystem_tool",
        "arguments": {"operation": "read", "path": "test.txt"},
        "permission_decision": "allowed",
        "response": "File contents here",
        "latency_ms": 100
    })
    
    # 3. Output/llm_call
    recorder.record_event({
        "event_type": "llm_call",
        "timestamp": 1002.0,
        "prompt": "Here are the contents: File contents here",
        "completion": "The file contains text.",
        "provider": "openai",
        "model": "gpt-4",
        "input_tokens": 30,
        "output_tokens": 15,
        "finish_reason": "stop",
        "latency_ms": 400
    })

def generate_failed_trace(trace_path: str):
    if os.path.exists(trace_path):
        os.remove(trace_path)
    recorder = ExecutionRecorder(trace_path)
    
    token = CapabilityToken() # Empty token, no permissions by default
    
    # 1. Denied tool call using real PermissionEngine
    tool1_name = "filesystem_tool"
    tool1_args = {"operation": "read", "path": "critical.sys"}
    allowed1, reason1 = check(token, tool1_name, tool1_args)
    
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 2001.0,
        "tool_name": tool1_name,
        "arguments": tool1_args,
        "permission_decision": "allowed" if allowed1 else "denied",
        "permission_reason": reason1 if not allowed1 else None,
        "response": "Success" if allowed1 else None,
        "latency_ms": 50
    })
    
    # 2. Allowed tool call with WRONG argument (we wanted query='hello', but execute 'goodbye')
    # HTTP token allow-list allows api.example.com
    token.http.allowed_domains.append("api.example.com")
    
    tool2_name = "http_tool"
    tool2_args = {"url": "http://api.example.com/search?q=goodbye"}
    allowed2, reason2 = check(token, tool2_name, tool2_args)
    
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 2002.0,
        "tool_name": tool2_name,
        "arguments": tool2_args,
        "permission_decision": "allowed" if allowed2 else "denied",
        "permission_reason": reason2 if not allowed2 else None,
        "response": "No results",
        "latency_ms": 150
    })

def main():
    metrics = [
        ToolSelectionAccuracy(),
        ArgumentCorrectness(),
        StepEfficiency(),
        GoalCompletionRate()
    ]
    
    # TEST 1: Simple run
    print("="*60)
    print("TEST 1: Simple Agent Run")
    print("="*60)
    simple_trace_path = "simple.trace"
    generate_simple_trace(simple_trace_path)
    
    tc1 = EvalTestCase(
        task_id="task-1",
        input="Read the file",
        expected_tool_calls=[{"tool": "filesystem_tool", "args": {"operation": "read", "path": "test.txt"}}],
        expected_final_state={"read_count": 1},
        expected_output_contains=[],
        max_steps=5,
        timeout_seconds=10.0
    )
    
    trace1 = trace_to_agent_trace(
        trace_path=simple_trace_path,
        task_id="task-1",
        input_text="Read the file",
        final_output="The file contains text.",
        actual_state={"read_count": 1}
    )
    
    res1 = run_eval(trace1, tc1, metrics)
    print("Raw output for simple run:")
    pprint(res1)
    
    # TEST 2: Failed/Denied Run
    print("\n" + "="*60)
    print("TEST 2: Trace with Denied Call & Bad Argument")
    print("="*60)
    failed_trace_path = "failed.trace"
    generate_failed_trace(failed_trace_path)
    
    tc2 = EvalTestCase(
        task_id="task-2",
        input="Delete sys file and search for hello",
        expected_tool_calls=[
            {"tool": "filesystem_tool", "args": {"operation": "read", "path": "critical.sys"}},
            {"tool": "http_tool", "args": {"url": "http://api.example.com/search?q=hello"}}
        ],
        expected_final_state={},
        expected_output_contains=[],
        max_steps=5,
        timeout_seconds=10.0
    )
    
    trace2 = trace_to_agent_trace(
        trace_path=failed_trace_path,
        task_id="task-2",
        input_text="Delete sys file and search for hello",
        final_output="Failed to complete task.",
        actual_state={}
    )
    
    res2 = run_eval(trace2, tc2, metrics)
    print("Raw output for failed run:")
    pprint(res2)
    
    print("\nVerification for Test 2:")
    ts_score = res2["metrics"]["Tool Selection Accuracy"].score
    ac_score = res2["metrics"]["Argument Correctness"].score
    
    print(f"Does ToolSelectionAccuracy correctly NOT count the denied call? Score: {ts_score}")
    if ts_score == 0.5:
        print("  -> YES (Score is 0.5 because http_tool was called, but filesystem_tool was hidden as expected).")
    else:
        print("  -> NO (Expected 0.5)")
        
    print(f"Does ArgumentCorrectness correctly score the bad argument as wrong? Score: {ac_score}")
    if ac_score == 0.0:
        print("  -> YES (Score is 0.0 because 'http_tool' was evaluated but the argument didn't match).")
    else:
        print("  -> NO (Expected 0.0)")

if __name__ == "__main__":
    main()
