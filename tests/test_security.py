from unittest.mock import patch
from typing import Any
from security.permission_engine import CapabilityToken, check, FilesystemCapability, DbCapability, HttpCapability

def test_filesystem_permission() -> None:
    token = CapabilityToken(
        filesystem=FilesystemCapability(
            read=["/workspace/public"],
            write=["/workspace/private"]
        )
    )
    
    # In-scope read
    allowed, reason = check(token, "filesystem_tool", {"operation": "read", "path": "/workspace/public/file.txt"})
    assert allowed == "executed"
    
    # In-scope write also allows read
    allowed, reason = check(token, "filesystem_tool", {"operation": "read", "path": "/workspace/private/file.txt"})
    assert allowed == "executed"
    
    # In-scope write
    allowed, reason = check(token, "filesystem_tool", {"operation": "write", "path": "/workspace/private/file.txt"})
    assert allowed == "executed"
    
    # Out-of-scope write
    allowed, reason = check(token, "filesystem_tool", {"operation": "write", "path": "/workspace/public/file.txt"})
    assert allowed == "permission_denied"
    assert "Write access denied" in reason
    
    # Missing path
    allowed, reason = check(token, "filesystem_tool", {"operation": "read"})
    assert allowed == "validation_error"
    assert "missing" in reason

    # Path traversal attempt (bypassing sandbox)
    allowed, reason = check(token, "filesystem_tool", {"operation": "write", "path": "/workspace/private/../public/file.txt"})
    assert allowed == "permission_denied"

def test_db_permission() -> None:
    token = CapabilityToken(
        db=DbCapability(read=True, write=False)
    )
    
    allowed, reason = check(token, "sqlite_tool", {"operation": "read", "query": "SELECT * FROM users"})
    assert allowed == "executed"
    
    allowed, reason = check(token, "sqlite_tool", {"operation": "write", "query": "DROP TABLE users"})
    assert allowed == "permission_denied"
    assert "write access denied" in reason.lower()

@patch('socket.gethostbyname')
def test_http_permission(mock_gethostbyname: Any) -> None:
    token = CapabilityToken(
        http=HttpCapability(allowed_domains=["example.com", "api.example.com", "localhost"])
    )
    
    mock_gethostbyname.return_value = "8.8.8.8"
    allowed, reason = check(token, "http_tool", {"url": "https://example.com/api/data"})
    assert allowed == "executed"
    
    allowed, reason = check(token, "http_tool", {"url": "https://api.example.com/"})
    assert allowed == "executed"
    
    allowed, reason = check(token, "http_tool", {"url": "https://malicious.com/"})
    assert allowed == "permission_denied"
    assert "Domain not in allow-list" in reason

    # Loopback IP check (DNS Rebinding/SSRF)
    mock_gethostbyname.return_value = "127.0.0.1"
    allowed, reason = check(token, "http_tool", {"url": "http://localhost:8080"})
    assert allowed == "executed"
