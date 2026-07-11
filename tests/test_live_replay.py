import os
import pytest
from pathlib import Path
from typing import List, Dict, Any

from replay.live_replay import LiveReplayRuntime
from recorder.recorder import ExecutionRecorder
from security.permission_engine import CapabilityToken
from security.rate_limiter import RateLimiter
from tools.base_tool import BaseTool, ToolResult
from recorder.trace_reader import TraceReader

class MockTool(BaseTool):
    name = "mock_tool"
    is_idempotent = True
    is_reversible = True
    
    # Needs a schema class but we can just use a dummy one for testing
    from pydantic import BaseModel
    class MockArgs(BaseModel):
        val: str
    schema_cls = MockArgs
        
    def _run(self, args: Any) -> dict[str, str]:
        return {"success": args.val}
        
def mock_agent(context: List[Dict[str, Any]], prompt: str) -> List[Dict[str, Any]]:
    return [
        {
            "type": "llm_call",
            "timestamp": 0.0,
            "prompt": prompt,
            "completion": "Test completion",
            "provider": "test",
            "model": "test",
            "input_tokens": 1,
            "output_tokens": 1,
            "finish_reason": "stop",
            "latency_ms": 1
        },
        {
            "type": "tool_call_request",
            "tool_name": "mock_tool",
            "arguments": {"val": "test"}
        }
    ]

def test_live_replay_runtime(tmp_path: Path) -> None:
    # 1. Create parent trace
    parent_trace = tmp_path / "parent.trace"
    recorder = ExecutionRecorder(parent_trace)
    recorder.record_event({
        "event_type": "llm_call",
        "timestamp": 100.0,
        "prompt": "Root prompt",
        "completion": "Root completion",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    
    # 2. Run LiveReplayRuntime
    branch_trace = tmp_path / "branch.trace"
    token = CapabilityToken()
    rate_limiter = RateLimiter()
    
    # Mock check so permission engine allows it
    # Since check() is hardcoded for specific tools in permission_engine, 
    # mock_tool will actually hit "Unknown tool: mock_tool" which results in validation_error.
    # That's perfectly fine to verify it flowed through the pipeline.
    
    runtime = LiveReplayRuntime(
        parent_trace_path=str(parent_trace),
        branch_trace_path=str(branch_trace),
        divergence_step_id="step-000001",
        agent_callable=mock_agent,
        capability_token=token,
        rate_limiter=rate_limiter,
        tools={"mock_tool": MockTool()}
    )
    
    runtime.run("New prompt")
    
    # 3. Verify recorded trace
    reader = TraceReader(branch_trace)
    events = list(reader.read_events())
    
    assert len(events) == 3 # Root 1, llm_call, tool_call
    assert events[0]["prompt"] == "Root prompt"
    assert events[1]["prompt"] == "New prompt"
    
    # Verify tool call was recorded with validation_error (because PermissionEngine doesn't know mock_tool)
    assert events[2]["event_type"] == "tool_call"
    assert events[2]["tool_name"] == "mock_tool"
    assert events[2]["permission_decision"] == "denied"
    assert events[2]["permission_reason"] == "Unknown tool: mock_tool"

def test_live_replay_permission_denied(tmp_path: Path) -> None:
    # 1. Create parent trace
    parent_trace = tmp_path / "parent_pd.trace"
    recorder = ExecutionRecorder(parent_trace)
    recorder.record_event({
        "event_type": "llm_call", "timestamp": 100.0,
        "prompt": "Root prompt", "completion": "Root completion",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    
    branch_trace = tmp_path / "branch_pd.trace"
    # An empty capability token means all operations are denied.
    token = CapabilityToken() 
    rate_limiter = RateLimiter()
    
    # We use a real tool (filesystem_tool) but ask for write, which is denied by empty token
    def pd_agent(context: List[Dict[str, Any]], prompt: str) -> List[Dict[str, Any]]:
        return [{
            "type": "tool_call_request",
            "tool_name": "filesystem_tool",
            "arguments": {"operation": "write", "path": "test.txt", "content": "data"}
        }]
        
    from tools.filesystem_tool import FilesystemTool
    runtime = LiveReplayRuntime(
        parent_trace_path=str(parent_trace),
        branch_trace_path=str(branch_trace),
        divergence_step_id="step-000001",
        agent_callable=pd_agent,
        capability_token=token,
        rate_limiter=rate_limiter,
        tools={"filesystem_tool": FilesystemTool(sandbox_root=str(tmp_path))}
    )
    
    runtime.run("New prompt")
    
    reader = TraceReader(branch_trace)
    events = list(reader.read_events())
    assert len(events) == 2 # Root 1, tool_call
    assert events[1]["event_type"] == "tool_call"
    assert events[1]["tool_name"] == "filesystem_tool"
    assert events[1]["permission_decision"] == "denied"
    assert "access denied" in events[1]["permission_reason"].lower()

def test_live_replay_rate_limited(tmp_path: Path) -> None:
    parent_trace = tmp_path / "parent_rl.trace"
    recorder = ExecutionRecorder(parent_trace)
    recorder.record_event({
        "event_type": "llm_call", "timestamp": 100.0,
        "prompt": "Root prompt", "completion": "Root completion",
        "provider": "p", "model": "m", "input_tokens": 1, "output_tokens": 1, "finish_reason": "stop", "latency_ms": 1
    })
    
    branch_trace = tmp_path / "branch_rl.trace"
    # Token allows read
    token = CapabilityToken()
    token.filesystem.read = [str(tmp_path)]
    rate_limiter = RateLimiter()
    
    # Pre-exhaust the rate limiter for filesystem_tool
    for _ in range(rate_limiter.config.max_calls_per_window):
        rate_limiter.check("filesystem_tool")
        
    def rl_agent(context: List[Dict[str, Any]], prompt: str) -> List[Dict[str, Any]]:
        return [{
            "type": "tool_call_request",
            "tool_name": "filesystem_tool",
            "arguments": {"operation": "read", "path": str(tmp_path / "test.txt")}
        }]
        
    from tools.filesystem_tool import FilesystemTool
    runtime = LiveReplayRuntime(
        parent_trace_path=str(parent_trace),
        branch_trace_path=str(branch_trace),
        divergence_step_id="step-000001",
        agent_callable=rl_agent,
        capability_token=token,
        rate_limiter=rate_limiter,
        tools={"filesystem_tool": FilesystemTool(sandbox_root=str(tmp_path))}
    )
    
    runtime.run("New prompt")
    
    reader = TraceReader(branch_trace)
    events = list(reader.read_events())
    assert len(events) == 2 # Root 1, tool_call
    assert events[1]["event_type"] == "tool_call"
    assert events[1]["tool_name"] == "filesystem_tool"
    # The tool was technically "allowed" by permissions, but rate limited.
    assert events[1]["permission_decision"] == "allowed"
    assert events[1]["rate_limit_decision"] == "rate_limited"
    assert "exceeded" in events[1]["rate_limit_reason"].lower()
