import os
from pathlib import Path
from pydantic import BaseModel, Field
from tools.base_tool import BaseTool

class FilesystemArguments(BaseModel):
    operation: str = Field(..., description="'read' or 'write'")
    path: str
    content: str = ""

class FilesystemTool(BaseTool):
    name = "filesystem_tool"
    is_idempotent = False # writes might not be idempotent, reads are
    is_reversible = False
    schema_cls = FilesystemArguments
    
    def __init__(self, sandbox_root: str):
        self.sandbox_root = Path(sandbox_root).resolve()
        
    def _run(self, args: FilesystemArguments) -> dict[str, str | bool]:
        target_path = Path(args.path).resolve()
        
        # Sandbox check: must use resolved paths and verify it is a descendant
        try:
            target_path.relative_to(self.sandbox_root)
        except ValueError:
            raise ValueError(f"Path outside sandbox: {args.path}")
            
        if args.operation == "read":
            with open(target_path, "r", encoding="utf-8") as f:
                return {"content": f.read()}
        elif args.operation == "write":
            # Ensure parent directories exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(args.content)
            return {"success": True}
        else:
            raise ValueError(f"Unknown operation: {args.operation}")
