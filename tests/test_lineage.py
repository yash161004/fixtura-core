import pytest
import os
from pathlib import Path
from recorder.recorder import ExecutionRecorder
from recorder.trace_reader import TraceReader, MissingParentTraceError

def test_backward_compatibility(tmp_path: Path) -> None:
    trace_path = tmp_path / "root.trace"
    recorder = ExecutionRecorder(trace_path)
    recorder.record_event({
        "event_type": "llm_call",
        "timestamp": 100.0,
        "prompt": "Hello",
        "completion": "World",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    
    events = list(TraceReader(trace_path).read_events())
    assert len(events) == 1
    assert events[0]["event_type"] == "llm_call"

def test_single_hop_branch(tmp_path: Path) -> None:
    # 1. Create root trace
    root_path = tmp_path / "root.trace"
    root_recorder = ExecutionRecorder(root_path)
    root_recorder.record_event({
        "event_type": "llm_call", "timestamp": 100.0,
        "prompt": "Root prompt 1", "completion": "completion 1",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    root_recorder.record_event({
        "event_type": "llm_call", "timestamp": 200.0,
        "prompt": "Root prompt 2", "completion": "completion 2",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    
    # 2. Create branch trace diverging at step-000001
    branch_path = tmp_path / "branch1.trace"
    branch_recorder = ExecutionRecorder(branch_path, parent_trace_id="root", divergence_step_id="step-000001")
    branch_recorder.record_event({
        "event_type": "llm_call", "timestamp": 300.0,
        "prompt": "Branch prompt", "completion": "Branch completion",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    
    events = list(TraceReader(branch_path).read_events())
    assert len(events) == 2
    assert events[0]["prompt"] == "Root prompt 1"
    assert events[0]["step_id"] == "step-000001"
    assert events[1]["prompt"] == "Branch prompt"

def test_multi_hop_branch(tmp_path: Path) -> None:
    # Root
    root_recorder = ExecutionRecorder(tmp_path / "t1.trace")
    root_recorder.record_event({
        "event_type": "llm_call", "timestamp": 100.0,
        "prompt": "Root 1", "completion": "c",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    
    # Branch 1 from Root
    b1_recorder = ExecutionRecorder(tmp_path / "t2.trace", parent_trace_id="t1", divergence_step_id="step-000001")
    b1_recorder.record_event({
        "event_type": "llm_call", "timestamp": 200.0,
        "prompt": "B1 1", "completion": "c",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    b1_recorder.record_event({
        "event_type": "llm_call", "timestamp": 300.0,
        "prompt": "B1 2", "completion": "c",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    
    # Branch 2 from Branch 1 (diverges at B1 1, which is step-000002)
    b2_recorder = ExecutionRecorder(tmp_path / "t3.trace", parent_trace_id="t2", divergence_step_id="step-000002")
    b2_recorder.record_event({
        "event_type": "llm_call", "timestamp": 400.0,
        "prompt": "B2 1", "completion": "c",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    
    events = list(TraceReader(tmp_path / "t3.trace").read_events())
    assert len(events) == 3
    assert events[0]["prompt"] == "Root 1"
    assert events[1]["prompt"] == "B1 1"
    assert events[2]["prompt"] == "B2 1"

def test_missing_parent_trace(tmp_path: Path) -> None:
    branch_path = tmp_path / "branch_orphaned.trace"
    branch_recorder = ExecutionRecorder(branch_path, parent_trace_id="missing", divergence_step_id="step-000001")
    branch_recorder.record_event({
        "event_type": "llm_call", "timestamp": 100.0,
        "prompt": "Branch", "completion": "c",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    
    with pytest.raises(MissingParentTraceError, match="Cannot resolve parent trace: missing"):
        list(TraceReader(branch_path).read_events())

def test_enum_round_trip(tmp_path: Path) -> None:
    trace_path = tmp_path / "enum.trace"
    recorder = ExecutionRecorder(trace_path)
    
    base_event = {
        "event_type": "tool_call",
        "timestamp": 100.0,
        "tool_name": "http_tool",
        "arguments": {"url": "foo"},
        "latency_ms": 10
    }
    
    # allowed
    e1 = dict(base_event)
    e1.update({"permission_decision": "allowed", "response": {"status": 200}})
    recorder.record_event(e1)
    
    # denied
    e2 = dict(base_event)
    e2.update({"permission_decision": "denied", "permission_reason": "not allowed", "response": None})
    recorder.record_event(e2)
    
    # validation_error
    e3 = dict(base_event)
    e3.update({"permission_decision": "validation_error", "permission_reason": "schema missing", "response": None})
    recorder.record_event(e3)
    
    events = list(TraceReader(trace_path).read_events())
    assert len(events) == 3
    assert events[0]["permission_decision"] == "allowed"
    assert events[1]["permission_decision"] == "denied"
    assert events[2]["permission_decision"] == "validation_error"
