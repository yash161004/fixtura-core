from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, ValidationError
from security.permission_engine import CapabilityToken, check

class ToolResult(BaseModel):
    outcome: str  # "validation_error", "permission_denied", or "executed"
    result: Optional[Any] = None
    error: Optional[str] = None
    reason: Optional[str] = None

class BaseTool:
    name: str
    is_idempotent: bool
    is_reversible: bool
    schema_cls: Type[BaseModel]
    
    def execute(self, capability_token: CapabilityToken, arguments: Dict[str, Any]) -> ToolResult:
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
            
        # Execute tool
        try:
            result = self._run(validated)
            return ToolResult(outcome="executed", result=result)
        except Exception as e:
            # We treat execution error as "executed" but with an error payload.
            return ToolResult(outcome="executed", error=str(e))
            
    def _run(self, arguments: Any) -> Any:
        raise NotImplementedError
