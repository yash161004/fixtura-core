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

def generate_simple_trace(trace_path: str) -> None:
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

def generate_failed_trace(trace_path: str) -> None:
    if os.path.exists(trace_path):
        os.remove(trace_path)
    recorder = ExecutionRecorder(trace_path)
    
    token = CapabilityToken() # Empty token, no permissions by default
    
    # 1. Denied tool call using real PermissionEngine
    tool1_name = "filesystem_tool"
    tool1_args = {"operation": "read", "path": "critical.sys"}
    allowed1, reason1 = check(token, tool1_name, tool1_args)
    assert allowed1 == "permission_denied"
    
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 2001.0,
        "tool_name": tool1_name,
        "arguments": tool1_args,
        "permission_decision": "denied",
        "permission_reason": reason1,
        "response": None,
        "latency_ms": 50
    })
    
    # 2. Allowed tool call with WRONG argument (we wanted query='hello', but execute 'goodbye')
    # HTTP token allow-list allows api.example.com
    token.http.allowed_domains.append("api.example.com")
    
    tool2_name = "http_tool"
    tool2_args = {"url": "http://api.example.com/search?q=goodbye"}
    allowed2, reason2 = check(token, tool2_name, tool2_args)
    assert allowed2 == "executed"
    
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 2002.0,
        "tool_name": tool2_name,
        "arguments": tool2_args,
        "permission_decision": "allowed",
        "permission_reason": None,
        "response": "No results",
        "latency_ms": 150
    })

def test_openeval_consistency() -> None:
    metrics = [
        ToolSelectionAccuracy(),
        ArgumentCorrectness(),
        StepEfficiency(),
        GoalCompletionRate()
    ]
    
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
    res2 = run_eval(trace1, tc1, metrics)
    
    assert res1 == res2, "OpenEval adapter must produce consistent trajectory-level results across runs"

def test_denied_tool_call_scoring() -> None:
    metrics = [
        ToolSelectionAccuracy(),
        ArgumentCorrectness(),
        StepEfficiency(),
        GoalCompletionRate()
    ]
    
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
    
    ts_score = res2["metrics"]["Tool Selection Accuracy"].score
    ac_score = res2["metrics"]["Argument Correctness"].score
    
    assert ts_score == 0.5
    assert ac_score == 0.0

def generate_complex_trace(trace_path: str) -> None:
    if os.path.exists(trace_path):
        os.remove(trace_path)
    recorder = ExecutionRecorder(trace_path)
    
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 3001.0,
        "tool_name": "http_tool",
        "arguments": {"url": "http://api.example.com/start"},
        "permission_decision": "allowed",
        "permission_reason": None,
        "response": "OK",
        "latency_ms": 50
    })
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 3002.0,
        "tool_name": "sqlite_tool",
        "arguments": {"operation": "write", "query": "INSERT"},
        "permission_decision": "denied",
        "permission_reason": "No write access",
        "response": None,
        "latency_ms": 50
    })

def generate_self_correction_trace(trace_path: str) -> None:
    if os.path.exists(trace_path):
        os.remove(trace_path)
    recorder = ExecutionRecorder(trace_path)
    
    # 1. Invalid args
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 4001.0,
        "tool_name": "filesystem_tool",
        "arguments": {"path": "only"},
        "permission_decision": "denied",
        "permission_reason": "Missing operation",
        "response": None,
        "latency_ms": 10
    })
    # 2. Corrected args
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 4002.0,
        "tool_name": "filesystem_tool",
        "arguments": {"operation": "read", "path": "valid.txt"},
        "permission_decision": "allowed",
        "permission_reason": None,
        "response": "Success",
        "latency_ms": 10
    })

def test_complex_scenario_scoring() -> None:
    metrics = [ToolSelectionAccuracy(), ArgumentCorrectness(), StepEfficiency(), GoalCompletionRate()]
    trace_path = "complex.trace"
    generate_complex_trace(trace_path)
    
    tc3 = EvalTestCase(
        task_id="task-3",
        input="Do two things",
        expected_tool_calls=[
            {"tool": "http_tool", "args": {"url": "http://api.example.com/start"}},
            {"tool": "sqlite_tool", "args": {"operation": "write", "query": "INSERT"}}
        ],
        expected_final_state={},
        expected_output_contains=[],
        max_steps=5,
        timeout_seconds=10.0
    )
    
    trace3 = trace_to_agent_trace(
        trace_path=trace_path,
        task_id="task-3",
        input_text="Do two things",
        final_output="Done",
        actual_state={}
    )
    
    res3 = run_eval(trace3, tc3, metrics)
    assert res3["metrics"]["Tool Selection Accuracy"].score == 0.5

def test_self_correction_scoring() -> None:
    metrics = [ToolSelectionAccuracy(), ArgumentCorrectness(), StepEfficiency(), GoalCompletionRate()]
    trace_path = "correction.trace"
    generate_self_correction_trace(trace_path)
    
    tc4 = EvalTestCase(
        task_id="task-4",
        input="Read valid.txt",
        expected_tool_calls=[
            {"tool": "filesystem_tool", "args": {"operation": "read", "path": "valid.txt"}}
        ],
        expected_final_state={},
        expected_output_contains=[],
        max_steps=5,
        timeout_seconds=10.0
    )
    
    trace4 = trace_to_agent_trace(
        trace_path=trace_path,
        task_id="task-4",
        input_text="Read valid.txt",
        final_output="Done",
        actual_state={}
    )
    
    res4 = run_eval(trace4, tc4, metrics)
    assert res4["metrics"]["Tool Selection Accuracy"].score == 1.0
import sys
import importlib
import pytest

def test_openeval_import_failure() -> None:
    # Save the original module if it exists
    saved_modules = {}
    for k in list(sys.modules.keys()):
        if k.startswith('openeval'):
            saved_modules[k] = sys.modules.pop(k)
    
    # Force sys.modules to say openeval is None, simulating it not being installed
    sys.modules['openeval'] = None  # type: ignore
    
    try:
        # We need to remove the already imported openeval_adapter to force a reload
        if 'tools.openeval_adapter' in sys.modules:
            del sys.modules['tools.openeval_adapter']
            
        with pytest.raises(RuntimeError) as exc_info:
            import tools.openeval_adapter
            
        assert "OpenEval is required for the eval adapter but not installed" in str(exc_info.value)
    finally:
        # Restore the original state so subsequent tests aren't broken
        del sys.modules['openeval']
        for k, v in saved_modules.items():
            sys.modules[k] = v
        
        if 'tools.openeval_adapter' in sys.modules:
            del sys.modules['tools.openeval_adapter']
        import tools.openeval_adapter
