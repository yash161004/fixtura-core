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
    assert allowed is True
    
    # In-scope write also allows read
    allowed, reason = check(token, "filesystem_tool", {"operation": "read", "path": "/workspace/private/file.txt"})
    assert allowed is True
    
    # In-scope write
    allowed, reason = check(token, "filesystem_tool", {"operation": "write", "path": "/workspace/private/file.txt"})
    assert allowed is True
    
    # Out-of-scope write
    allowed, reason = check(token, "filesystem_tool", {"operation": "write", "path": "/workspace/public/file.txt"})
    assert allowed is False
    assert "Write access denied" in reason
    
    # Missing path
    allowed, reason = check(token, "filesystem_tool", {"operation": "read"})
    assert allowed is False
    assert "missing" in reason

def test_db_permission() -> None:
    token = CapabilityToken(
        db=DbCapability(read=True, write=False)
    )
    
    allowed, reason = check(token, "sqlite_tool", {"operation": "read", "query": "SELECT * FROM users"})
    assert allowed is True
    
    allowed, reason = check(token, "sqlite_tool", {"operation": "write", "query": "DROP TABLE users"})
    assert allowed is False
    assert "write access denied" in reason.lower()

def test_http_permission() -> None:
    token = CapabilityToken(
        http=HttpCapability(allowed_domains=["example.com", "api.example.com"])
    )
    
    allowed, reason = check(token, "http_tool", {"url": "https://example.com/api/data"})
    assert allowed is True
    
    allowed, reason = check(token, "http_tool", {"url": "https://api.example.com/"})
    assert allowed is True
    
    allowed, reason = check(token, "http_tool", {"url": "https://malicious.com/"})
    assert allowed is False
    assert "Domain not in allow-list" in reason
