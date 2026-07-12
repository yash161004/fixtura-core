import time
from typing import Dict, List, Set, Tuple, Literal, Optional
from pydantic import BaseModel

class RateLimiterConfig(BaseModel):
    max_calls_per_session: int = 100
    max_calls_per_window: int = 20
    window_seconds: int = 60
    consecutive_failures_threshold: int = 3

class RateLimiter:
    def __init__(self, config: Optional[RateLimiterConfig] = None) -> None:
        self.config = config or RateLimiterConfig()
        
        # State
        self.session_calls: Dict[str, int] = {}
        self.window_calls: Dict[str, List[float]] = {}
        self.consecutive_failures: Dict[str, int] = {}
        self.circuit_broken: Set[str] = set()
        
    def check(self, tool_name: str, current_time: Optional[float] = None) -> Tuple[Literal['allowed', 'rate_limited', 'circuit_broken'], str]:
        """
        Checks if the tool is allowed to execute based on rate limits and circuit breaker status.
        If allowed, automatically increments the invocation counters.
        """
        if tool_name in self.circuit_broken:
            return "circuit_broken", f"Circuit breaker tripped for {tool_name} due to {self.config.consecutive_failures_threshold} consecutive failures."
            
        session_count = self.session_calls.get(tool_name, 0)
        if session_count >= self.config.max_calls_per_session:
            return "rate_limited", f"Session limit of {self.config.max_calls_per_session} calls exceeded for {tool_name}."
            
        now = current_time if current_time is not None else time.time()
        window = self.window_calls.setdefault(tool_name, [])
        cutoff = now - self.config.window_seconds
        
        # prune old calls
        window = [t for t in window if t > cutoff]
        self.window_calls[tool_name] = window
        
        if len(window) >= self.config.max_calls_per_window:
            return "rate_limited", f"Window limit of {self.config.max_calls_per_window} calls per {self.config.window_seconds}s exceeded for {tool_name}."
            
        # Allowed! Bump the counters now
        self.session_calls[tool_name] = session_count + 1
        self.window_calls[tool_name].append(now)
        
        return "allowed", ""

    def record_execution(self, tool_name: str, success: bool) -> None:
        """
        Called after tool execution to record success or failure for the circuit breaker.
        """
        if success:
            self.consecutive_failures[tool_name] = 0
        else:
            failures = self.consecutive_failures.get(tool_name, 0) + 1
            self.consecutive_failures[tool_name] = failures
            if failures >= self.config.consecutive_failures_threshold:
                self.circuit_broken.add(tool_name)
