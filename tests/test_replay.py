import json
import pytest
from typing import Dict, Any
from unittest.mock import patch
from pathlib import Path
from recorder.recorder import ExecutionRecorder
from recorder.trace_reader import TraceReader, TraceValidationError
from replay.passive_replay import PassiveReplay
from replay.step_inspector import StepInspector

def test_trace_validation(tmp_path: Path) -> None:
    trace_file = tmp_path / "invalid.trace"
    recorder = ExecutionRecorder(trace_file)
    
    # Intentionally bypass sanitizer to inject malformed events for the test
    import zstandard as zstd
    cctx = zstd.ZstdCompressor()
    
    def write_raw(data: Dict[str, Any]) -> None:
        with open(trace_file, "ab") as f:
            f.write(cctx.compress((json.dumps(data) + "\n").encode("utf-8")))

    # 1. Missing step_id
    write_raw({"event_type": "llm_call"})
    reader = TraceReader(trace_file)
    with pytest.raises(TraceValidationError, match="Missing required field: step_id"):
        list(reader.read_events())
        
    trace_file.unlink()

    # 2. Duplicate step_id
    write_raw({"step_id": "step-1", "timestamp": "t", "event_type": "llm_call", "prompt": "", "completion": "", "provider": "", "model": "", "input_tokens": 0, "output_tokens": 0, "finish_reason": "", "latency_ms": 0})
    write_raw({"step_id": "step-1", "timestamp": "t", "event_type": "llm_call", "prompt": "", "completion": "", "provider": "", "model": "", "input_tokens": 0, "output_tokens": 0, "finish_reason": "", "latency_ms": 0})
    
    reader = TraceReader(trace_file)
    events = reader.read_events()
    next(events) # First one passes
    with pytest.raises(TraceValidationError, match="Duplicate step_id detected: step-1"):
        next(events)
        
    trace_file.unlink()
    
    # 3. Invalid event_type
    write_raw({"step_id": "step-1", "timestamp": "t", "event_type": "unknown"})
    reader = TraceReader(trace_file)
    with pytest.raises(TraceValidationError, match="Invalid event_type: unknown"):
        list(reader.read_events())
        
    trace_file.unlink()

    # 4. Denied with non-string reason
    write_raw({"step_id": "step-1", "timestamp": "t", "event_type": "tool_call", "tool_name": "t", "arguments": {}, "permission_decision": "denied", "permission_reason": 123, "response": None, "latency_ms": 0})
    reader = TraceReader(trace_file)
    with pytest.raises(TraceValidationError, match="permission_reason must be a string when permission_decision is denied"):
        list(reader.read_events())

def test_monotonic_step_id(tmp_path: Path) -> None:
    trace_file = tmp_path / "monotonic.trace"
    recorder = ExecutionRecorder(trace_file)
    
    # Provide explicitly incorrect step_ids to test overwrite behavior
    for i in range(5):
        recorder.record_event({
            "step_id": "i_should_be_overwritten",
            "timestamp": "t",
            "event_type": "tool_call",
            "tool_name": "t",
            "arguments": {},
            "permission_decision": "allowed",
            "response": {},
            "latency_ms": 0
        })
        
    reader = TraceReader(trace_file)
    events = list(reader.read_events())
    
    assert len(events) == 5
    for i, event in enumerate(events):
        assert event["step_id"] == f"step-{i+1:06d}"

def test_passive_replay_no_live_calls(tmp_path: Path) -> None:
    trace_file = tmp_path / "passive.trace"
    recorder = ExecutionRecorder(trace_file)
    
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": "t",
        "tool_name": "safe_tool",
        "arguments": {},
        "permission_decision": "allowed",
        "response": {"data": "ok"},
        "latency_ms": 10
    })
    
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": "t",
        "tool_name": "danger_tool",
        "arguments": {},
        "permission_decision": "denied",
        "permission_reason": "No access",
        "response": None,
        "latency_ms": 5
    })
    
    replay = PassiveReplay(trace_file)
    
    # Mock ANY hypothetical live clients or execution engines.
    # Since passive replay shouldn't have imports for live clients natively, 
    # we assert that its `run()` executes smoothly without invoking any actual 
    # external runtime modules via internal patch verification.
    with patch("security.permission_engine.check") as mock_check:
        mock_check.side_effect = RuntimeError("PermissionEngine should never be called during replay")
        # Run should complete entirely using purely stored trace payloads
        outputs = list(replay.run())
        
    assert mock_check.call_count == 0
    # Assert exact output sequence match
    assert len(outputs) == 2
    assert outputs[0] == {"status": "success", "result": {"data": "ok"}}
    assert outputs[1] == {"status": "denied", "reason": "No access"}

def test_passive_replay_exception_handling(tmp_path: Path) -> None:
    trace_file = tmp_path / "exception.trace"
    recorder = ExecutionRecorder(trace_file)
    
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": "t",
        "tool_name": "failing_tool",
        "arguments": {},
        "permission_decision": "allowed",
        "response": None,
        "exception": "Connection reset by peer",
        "latency_ms": 100
    })
    
    replay = PassiveReplay(trace_file)
    
    # Must explicitly re-raise or reproduce the exception, not swallow it
    with pytest.raises(RuntimeError, match="Recorded tool_call failed: Connection reset by peer"):
        list(replay.run())

def test_step_inspection(tmp_path: Path) -> None:
    trace_file = tmp_path / "inspector.trace"
    recorder = ExecutionRecorder(trace_file)
    
    recorder.record_event({"timestamp": "t", "event_type": "llm_call", "prompt": "a", "completion": "b", "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1})
    recorder.record_event({"timestamp": "t", "event_type": "llm_call", "prompt": "c", "completion": "d", "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1})
    
    inspector = StepInspector(trace_file)
    
    # Verify no stray mutation methods exist on the inspector
    public_methods = [m for m in dir(inspector) if not m.startswith('_')]
    assert set(public_methods) == {"advance", "current_step"}
    
    # Starts empty
    assert inspector.current_step() == {}
    
    # Advance exactly one step
    assert inspector.advance() is True
    step1 = inspector.current_step()
    assert step1["prompt"] == "a"
    
    # Verify mutation isolation (modifying returned dict shouldn't mutate inspector state)
    step1["prompt"] = "hacked"
    assert inspector.current_step()["prompt"] == "a"
    
    # Advance to second step
    assert inspector.advance() is True
    step2 = inspector.current_step()
    assert step2["prompt"] == "c"
    
    # EOF reached
    assert inspector.advance() is False
    assert inspector.current_step() == {}
