from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, ValidationError
from security.permission_engine import CapabilityToken, check
from security.rate_limiter import RateLimiter
class ToolResult(BaseModel):
    outcome: str  # "validation_error", "permission_denied", "rate_limited", "circuit_broken", or "executed"
    result: Optional[Any] = None
    error: Optional[str] = None
    reason: Optional[str] = None

class BaseTool:
    name: str
    is_idempotent: bool
    is_reversible: bool
    schema_cls: Type[BaseModel]
    
    def execute(self, capability_token: CapabilityToken, arguments: Dict[str, Any], rate_limiter: RateLimiter) -> ToolResult:
        # Schema validation (pydantic) runs first
        try:
            validated = self.schema_cls(**arguments)
        except ValidationError as e:
            return ToolResult(outcome="validation_error", error=str(e))
            
        # check() runs on validated arguments
        status, reason = check(capability_token, self.name, validated.model_dump())
        if status == "permission_denied":
            return ToolResult(outcome="permission_denied", reason=reason)
        elif status == "validation_error":
            return ToolResult(outcome="validation_error", error=reason)
            
        # Enforce rate limit and circuit breaker
        rl_status, rl_reason = rate_limiter.check(self.name)
        if rl_status != "allowed":
            return ToolResult(outcome=rl_status, reason=rl_reason)
            
        # Execute tool
        try:
            result = self._run(validated)
            rate_limiter.record_execution(self.name, success=True)
            return ToolResult(outcome="executed", result=result)
        except Exception as e:
            rate_limiter.record_execution(self.name, success=False)
            # We treat execution error as "executed" but with an error payload.
            return ToolResult(outcome="executed", error=str(e))
            
    def _run(self, arguments: Any) -> Any:
        raise NotImplementedError
