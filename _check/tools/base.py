from typing import Any, Dict, Tuple
from pydantic import BaseModel

class BaseTool:
    """
    Base interface for all Phase 1 Fixtura execution tools.
    """
    name: str = ""
    is_idempotent: bool = False
    is_reversible: bool = False
    
    class InputSchema(BaseModel):
        pass

    def execute(self, arguments: Dict[str, Any]) -> Tuple[bool, Any]:
        """
        Executes the tool with the given pre-validated and pre-authorized arguments.
        Returns a tuple of (success, result).
        """
        raise NotImplementedError
