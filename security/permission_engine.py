from typing import Any, Dict, List, Tuple, Literal
from pydantic import BaseModel, Field
from pathlib import Path

class FilesystemCapability(BaseModel):
    read: List[str] = Field(default_factory=list)
    write: List[str] = Field(default_factory=list)

class DbCapability(BaseModel):
    read: bool = False
    write: bool = False

class HttpCapability(BaseModel):
    allowed_domains: List[str] = Field(default_factory=list)

class CapabilityToken(BaseModel):
    filesystem: FilesystemCapability = Field(default_factory=FilesystemCapability)
    db: DbCapability = Field(default_factory=DbCapability)
    http: HttpCapability = Field(default_factory=HttpCapability)

def _is_path_in_allowed(path: str, allowed_paths: List[str]) -> bool:
    try:
        target_path = Path(path).resolve()
    except Exception:
        return False
        
    for allowed in allowed_paths:
        try:
            allowed_path = Path(allowed).resolve()
            # Check if target is same as or descendant of allowed
            target_path.relative_to(allowed_path)
            return True
        except ValueError:
            continue
    return False

def check(capability_token: CapabilityToken, tool_name: str, arguments: Dict[str, Any]) -> Tuple[Literal['executed', 'permission_denied', 'validation_error'], str]:
    """
    Checks if the tool execution is allowed by the capability token.
    Returns (allowed, reason).
    """
    if tool_name == "filesystem_tool":
        operation = arguments.get("operation")
        path = arguments.get("path")
        
        if not path:
            return "validation_error", "Filesystem path missing."
            
        if operation == "read":
            if not _is_path_in_allowed(path, capability_token.filesystem.read) and \
               not _is_path_in_allowed(path, capability_token.filesystem.write):
                return "permission_denied", f"Read access denied for path: {path}"
            return "executed", ""
        elif operation == "write":
            if not _is_path_in_allowed(path, capability_token.filesystem.write):
                return "permission_denied", f"Write access denied for path: {path}"
            return "executed", ""
        else:
            return "validation_error", f"Unknown filesystem operation: {operation}"
            
    elif tool_name == "sqlite_tool":
        operation = arguments.get("operation")
        if operation == "read":
            if not capability_token.db.read:
                return "permission_denied", "Database read access denied."
            return "executed", ""
        elif operation == "write":
            if not capability_token.db.write:
                return "permission_denied", "Database write access denied."
            return "executed", ""
        else:
            return "validation_error", f"Unknown database operation: {operation}"
            
    elif tool_name == "http_tool":
        url = arguments.get("url")
        if not url:
            return "validation_error", "URL missing."
            
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.hostname
        if not domain:
            return "validation_error", "Invalid URL."
            
        if domain not in capability_token.http.allowed_domains:
            return "permission_denied", f"Domain not in allow-list: {domain}"
            
        return "executed", ""
        
    else:
        return "validation_error", f"Unknown tool: {tool_name}"
