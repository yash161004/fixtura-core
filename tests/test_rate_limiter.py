import pytest
from typing import Any, Dict
from pydantic import BaseModel
from security.rate_limiter import RateLimiter, RateLimiterConfig
from tools.base_tool import BaseTool, ToolResult
from security.permission_engine import CapabilityToken

class DummySchema(BaseModel):
    pass

class DummyTool(BaseTool):
    name = "dummy_tool"
    is_idempotent = True
    is_reversible = False
    schema_cls = DummySchema
    
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        
    def _run(self, arguments: Any) -> Any:
        if self.should_fail:
            raise Exception("Simulated failure")
        return "success"

def test_rate_limiter_session_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tools.base_tool.check", lambda token, name, args: ("executed", ""))
    config = RateLimiterConfig(max_calls_per_session=2, max_calls_per_window=10)
    limiter = RateLimiter(config=config)
    tool = DummyTool()
    token = CapabilityToken()
    
    # Call 1
    res1 = tool.execute(token, {}, rate_limiter=limiter)
    assert res1.outcome == "executed"
    
    # Call 2
    res2 = tool.execute(token, {}, rate_limiter=limiter)
    assert res2.outcome == "executed"
    
    # Call 3 - Should be rate limited
    res3 = tool.execute(token, {}, rate_limiter=limiter)
    assert res3.outcome == "rate_limited"
    assert "Session limit" in str(res3.reason)

def test_rate_limiter_window_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tools.base_tool.check", lambda token, name, args: ("executed", ""))
    config = RateLimiterConfig(max_calls_per_session=10, max_calls_per_window=2, window_seconds=60)
    limiter = RateLimiter(config=config)
    tool = DummyTool()
    token = CapabilityToken()
    
    # Mocking time for the check
    # We will just call the limiter directly to simulate time
    
    # t = 0
    status, _ = limiter.check("dummy_tool", current_time=0.0)
    assert status == "allowed"
    limiter.record_execution("dummy_tool", success=True)
    
    # t = 10
    status, _ = limiter.check("dummy_tool", current_time=10.0)
    assert status == "allowed"
    limiter.record_execution("dummy_tool", success=True)
    
    # t = 20 (N+1 in window)
    status, reason = limiter.check("dummy_tool", current_time=20.0)
    assert status == "rate_limited"
    assert "Window limit" in reason
    
    # t = 65 (first call fell out of window)
    status, _ = limiter.check("dummy_tool", current_time=65.0)
    assert status == "allowed"
    limiter.record_execution("dummy_tool", success=True)

def test_circuit_breaker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tools.base_tool.check", lambda token, name, args: ("executed", ""))
    config = RateLimiterConfig(consecutive_failures_threshold=3)
    limiter = RateLimiter(config=config)
    tool_fail = DummyTool(should_fail=True)
    tool_success = DummyTool(should_fail=False)
    token = CapabilityToken()
    
    # 1st failure
    res = tool_fail.execute(token, {}, rate_limiter=limiter)
    assert res.outcome == "executed" # It executed but failed
    assert res.error is not None
    
    # 2nd failure
    res = tool_fail.execute(token, {}, rate_limiter=limiter)
    assert res.outcome == "executed"
    
    # Interleaved success resets the breaker
    res = tool_success.execute(token, {}, rate_limiter=limiter)
    assert res.outcome == "executed"
    assert limiter.consecutive_failures["dummy_tool"] == 0
    
    # 3 consecutive failures
    tool_fail.execute(token, {}, rate_limiter=limiter)
    tool_fail.execute(token, {}, rate_limiter=limiter)
    tool_fail.execute(token, {}, rate_limiter=limiter)
    
    # 4th call should trip circuit breaker immediately in the execute layer
    res_trip = tool_success.execute(token, {}, rate_limiter=limiter)
    assert res_trip.outcome == "circuit_broken"
    assert "Circuit breaker tripped" in str(res_trip.reason)
