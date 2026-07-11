import json
import pytest
from pathlib import Path
from recorder.recorder import ExecutionRecorder
from tools import viewer, html_viewer

@pytest.fixture
def sample_trace(tmp_path: Path) -> Path:
    """
    Generate a dynamic .trace file using an actual Recorder run.
    This guarantees the viewer is consuming real, up-to-date schema outputs.
    """
    trace_file = tmp_path / "test_viewer.trace"
    recorder = ExecutionRecorder(trace_file)
    
    event1 = {
        "event_type": "llm_call",
        "timestamp": "2026-07-06T00:00:00Z",
        "step_id": "step1",
        "prompt": "Hello",
        "completion": "World",
        "password": "my_secret_password", # Should be sanitized
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 100
    }
    
    event2 = {
        "event_type": "tool_call",
        "timestamp": "2026-07-06T00:00:01Z",
        "step_id": "step2",
        "tool_name": "http_tool",
        "arguments": {"url": "http://example.com"},
        "permission_decision": "allowed",
        "response": {"status": 200},
        "latency_ms": 150
    }

    event3 = {
        "event_type": "tool_call",
        "timestamp": "2026-07-06T00:00:02Z",
        "step_id": "step3",
        "tool_name": "rm_tool",
        "arguments": {"path": "/etc/passwd"},
        "permission_decision": "denied",
        "permission_reason": "Path /etc/passwd is outside allowed workspace.",
        "response": None,
        "latency_ms": 10
    }
    
    recorder.record_event(event1)
    recorder.record_event(event2)
    recorder.record_event(event3)
    
    return trace_file

def test_cli_viewer(sample_trace: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Setup sys.argv exactly as cli.view wrapper would
    monkeypatch.setattr("sys.argv", ["fixtura view", str(sample_trace)])
    
    viewer.main()
    
    captured = capsys.readouterr()
    stdout = captured.out

    # 1. Check order/steps
    assert "Step 1 [step1] | Type: \x1b[96mllm_call" in stdout
    assert "Step 2 [step2] | Type: \x1b[96mtool_call" in stdout
    assert "Step 3 [step3] | Type: \x1b[96mtool_call" in stdout

    # 2. Check tool names
    assert "Tool:\x1b[0m \x1b[93mhttp_tool\x1b[0m" in stdout
    assert "Tool:\x1b[0m \x1b[93mrm_tool\x1b[0m" in stdout

    # 3. Check latency
    assert "Latency: 100ms" in stdout
    assert "Latency: 150ms" in stdout
    assert "Latency: 10ms" in stdout

    # 4. Check allowed/denied and reasons
    assert "Permission:\x1b[0m \x1b[92mALLOWED\x1b[0m" in stdout
    assert "Permission:\x1b[0m \x1b[91mDENIED\x1b[0m" in stdout
    assert "Path /etc/passwd is outside allowed workspace." in stdout

    # 5. Check what was recorded (sanitized)
    assert "[REDACTED]" in stdout  # from password field in llm_call
    assert "Hello" in stdout
    assert "World" in stdout
    assert "http://example.com" in stdout

def test_html_viewer(sample_trace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out_html = tmp_path / "viewer.html"
    monkeypatch.setattr("sys.argv", ["fixtura html-view", str(sample_trace), "-o", str(out_html)])
    
    html_viewer.main()
    
    assert out_html.exists()
    html_content = out_html.read_text(encoding="utf-8")
    
    # 1. Check order/steps
    assert "Step 1 [step1]" in html_content
    assert "Type: llm_call" in html_content
    assert "Step 2 [step2]" in html_content
    assert "Step 3 [step3]" in html_content
    
    # 2. Check tool names
    assert '<span class="tool-name">http_tool</span>' in html_content
    assert '<span class="tool-name">rm_tool</span>' in html_content
    
    # 3. Check latency
    assert "Latency: 100ms" in html_content
    assert "Latency: 150ms" in html_content
    
    # 4. Check allowed/denied and reasons
    assert '<span class="allowed">ALLOWED</span>' in html_content
    assert '<span class="denied">DENIED</span>' in html_content
    assert "Path /etc/passwd is outside allowed workspace." in html_content
    
    # 5. Check what was recorded
    assert "[REDACTED]" in html_content
    assert "Hello" in html_content
    assert "http://example.com" in html_content
