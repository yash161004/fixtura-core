import json
import pytest
import threading
from pathlib import Path
from recorder.recorder import ExecutionRecorder
from recorder.trace_reader import TraceReader

def test_recorder_zstd_compression(tmp_path: Path) -> None:
    trace_file = tmp_path / "test.trace"
    recorder = ExecutionRecorder(trace_file)
    
    event1 = {
        "event_type": "llm_call",
        "timestamp": "2026-07-06T00:00:00Z",
        "step_id": "step1",
        "prompt": "Hello",
        "completion": "World",
        "password": "my_secret_password",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    }
    
    event2 = {
        "event_type": "tool_call",
        "timestamp": "2026-07-06T00:00:00Z",
        "step_id": "step2",
        "tool_name": "http_tool",
        "arguments": {"url": "http://example.com"},
        "permission_decision": "allowed",
        "response": {"status": 200},
        "latency_ms": 10
    }
    
    recorder.record_event(event1)
    recorder.record_event(event2)
    
    assert trace_file.exists()
    
    # Use TraceReader to read events
    reader = TraceReader(trace_file)
    events = list(reader.read_events())
    
    assert len(events) == 2
    
    loaded_event1 = events[0]
    loaded_event2 = events[1]
    
    assert loaded_event1["event_type"] == "llm_call"
    # Ensure sanitization ran
    assert loaded_event1["password"] == "[REDACTED]"
    
    assert loaded_event2["event_type"] == "tool_call"
    assert loaded_event2["tool_name"] == "http_tool"

def test_recorder_concurrency(tmp_path: Path) -> None:
    trace_file = tmp_path / "concurrency.trace"
    recorder = ExecutionRecorder(trace_file)
    
    num_threads = 10
    events_per_thread = 50
    
    def worker(thread_idx: int) -> None:
        for i in range(events_per_thread):
            recorder.record_event({
                "event_type": "tool_call",
                "timestamp": "2026-07-06T00:00:00Z",
                "thread_idx": thread_idx,
                "event_idx": i,
                "tool_name": "t",
                "arguments": {},
                "permission_decision": "allowed",
                "response": {},
                "latency_ms": 0
            })
            
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)
        
    for t in threads:
        t.join()
        
    reader = TraceReader(trace_file)
    events = list(reader.read_events())
    
    # Assert correct total event count and successful parsing
    assert len(events) == num_threads * events_per_thread
    assert all(e["event_type"] == "tool_call" for e in events)

def test_trace_reader_validates_permission_reason_is_string(tmp_path: Path) -> None:
    from recorder.trace_reader import TraceValidationError
    trace_file = tmp_path / "test_reason.trace"
    recorder = ExecutionRecorder(trace_file)
    from typing import Dict, Any
    event: Dict[str, Any] = {
        "event_type": "tool_call",
        "timestamp": "2026-07-06T00:00:00Z",
        "step_id": "step1",
        "tool_name": "http_tool",
        "arguments": {},
        "permission_decision": "denied",
        "permission_reason": None,
        "latency_ms": 10
    }
    recorder.record_event(event)
    
    reader = TraceReader(trace_file)
    with pytest.raises(TraceValidationError, match="permission_reason required when permission_decision is denied"):
        list(reader.read_events())
