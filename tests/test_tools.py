from security.rate_limiter import RateLimiter
import os
import sqlite3
import pytest
from pathlib import Path
from typing import Any, Callable, Type
from tools.filesystem_tool import FilesystemTool
from tools.sqlite_tool import SqliteTool
from tools.http_tool import HttpTool
from security.permission_engine import CapabilityToken, FilesystemCapability, DbCapability, HttpCapability

def test_filesystem_schema_validation() -> None:
    tool = FilesystemTool(sandbox_root="/tmp/sandbox")
    token = CapabilityToken()
    
    # Missing required 'operation' and 'path'
    res = tool.execute(token, {}, rate_limiter=RateLimiter())
    assert res.outcome == "validation_error"
    assert res.error is not None
    assert "operation" in res.error
    assert "path" in res.error

def test_filesystem_sandbox_traversal(tmp_path: Path) -> None:
    # tmp_path is our sandbox
    tool = FilesystemTool(sandbox_root=str(tmp_path))
    # Give the permission engine broad access (the parent directory) so it doesn't block the request,
    # ensuring we are testing the tool's sandbox logic.
    token = CapabilityToken(filesystem=FilesystemCapability(write=[str(tmp_path.parent)]))
    
    # Valid write
    valid_file = tmp_path / "test.txt"
    res = tool.execute(token, {"operation": "write", "path": str(valid_file), "content": "data"}, rate_limiter=RateLimiter())
    assert res.outcome == "executed"
    
    # Path traversal attempt
    traversal_path = tmp_path / ".." / "etc" / "passwd"
    res = tool.execute(token, {"operation": "write", "path": str(traversal_path), "content": "data"}, rate_limiter=RateLimiter())
    assert res.outcome == "executed"
    assert res.error is not None
    assert "outside sandbox" in res.error

def test_filesystem_symlink_escape(tmp_path: Path) -> None:
    tool = FilesystemTool(sandbox_root=str(tmp_path))
    # Grant broad permission so permission engine doesn't block it, testing tool's sandbox instead
    token = CapabilityToken(filesystem=FilesystemCapability(write=[str(tmp_path.parent)], read=[str(tmp_path.parent)]))
    
    # Create an outside directory
    outside_dir = tmp_path.parent / "outside"
    outside_dir.mkdir(exist_ok=True)
    (outside_dir / "secret.txt").write_text("secret")
    
    # Create a symlink inside the sandbox pointing outside
    symlink_path = tmp_path / "link_out"
    try:
        os.symlink(str(outside_dir), str(symlink_path))
    except OSError:
        pytest.skip("Symlinks not supported on this OS/filesystem")
        
    res = tool.execute(token, {"operation": "read", "path": str(symlink_path / "secret.txt")}, rate_limiter=RateLimiter())
    assert res.outcome == "executed"
    assert res.error is not None
    assert "outside sandbox" in res.error

def test_sqlite_schema_validation() -> None:
    tool = SqliteTool(db_path=":memory:")
    token = CapabilityToken()
    
    res = tool.execute(token, {"query": "SELECT 1"}, rate_limiter=RateLimiter())
    assert res.outcome == "validation_error"
    assert res.error is not None
    assert "operation" in res.error

def test_sqlite_injection_neutralization(tmp_path: Path) -> None:
    db_file = tmp_path / "test.db"
    tool = SqliteTool(db_path=str(db_file))
    token = CapabilityToken(db=DbCapability(read=True, write=True))
    
    # Setup DB
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO users (name) VALUES ('admin')")
        conn.commit()
        
    # Attempt SQL injection via parameterized queries
    injection_payload = "admin' OR '1'='1"
    res = tool.execute(token, {
        "operation": "read", 
        "query": "SELECT * FROM users WHERE name = ?", 
        "parameters": [injection_payload]
    }, rate_limiter=RateLimiter())
    
    assert res.outcome == "executed"
    assert res.result is not None
    assert isinstance(res.result, dict)
    assert len(res.result["rows"]) == 0

def test_http_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    tool = HttpTool()
    token = CapabilityToken(http=HttpCapability(allowed_domains=["example.com"]))
    
    # Need to mock requests so it doesn't actually make network calls during test
    def mock_request(*args: Any, **kwargs: Any) -> Any:
        class MockResponse:
            status_code = 200
            headers: dict[str, str] = {}
            text = "ok"
        return MockResponse()
        
    monkeypatch.setattr("requests.request", mock_request)
    
    res = tool.execute(token, {"method": "GET", "url": "https://malicious.com"}, rate_limiter=RateLimiter())
    assert res.outcome == "permission_denied"

def test_http_ssrf_protection() -> None:
    tool = HttpTool()
    token = CapabilityToken(http=HttpCapability(allowed_domains=["127.0.0.1", "localhost", "example.com"]))
    
    # 127.0.0.1 is private/loopback
    res = tool.execute(token, {"method": "GET", "url": "http://127.0.0.1/admin"}, rate_limiter=RateLimiter())
    assert res.outcome == "executed"
    assert res.error is not None
    assert "private/loopback" in res.error
    
    # localhost resolves to 127.0.0.1
    res = tool.execute(token, {"method": "GET", "url": "http://localhost/admin"}, rate_limiter=RateLimiter())
    assert res.outcome == "executed"
    assert res.error is not None
    assert "private/loopback" in res.error

def test_http_dns_rebinding(monkeypatch: pytest.MonkeyPatch) -> None:
    tool = HttpTool()
    token = CapabilityToken(http=HttpCapability(allowed_domains=["rebind.example.com"]))
    
    resolution_count = 0
    def mock_gethostbyname(domain: str) -> str:
        nonlocal resolution_count
        resolution_count += 1
        if resolution_count == 1:
            return "8.8.8.8"  # safe IP on first check
        return "127.0.0.1"    # malicious private IP on second check (if a TOCTOU existed)
        
    monkeypatch.setattr("socket.gethostbyname", mock_gethostbyname)
    
    connected_ip = None
    import urllib3.util.connection
    def mock_create_connection(address: tuple[str, int], *args: Any, **kwargs: Any) -> Any:
        nonlocal connected_ip
        connected_ip = address[0]
        raise Exception("Mock connection closed")
        
    monkeypatch.setattr("urllib3.util.connection.create_connection", mock_create_connection)
    
    res = tool.execute(token, {"method": "GET", "url": "http://rebind.example.com/"}, rate_limiter=RateLimiter())
    
    assert res.outcome == "executed"
    assert res.error is not None
    assert "Mock connection closed" in res.error
    
    # The HTTP client MUST have attempted to connect to the FIRST resolved IP (8.8.8.8)
    assert connected_ip == "8.8.8.8"

def test_http_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    import concurrent.futures
    tool = HttpTool()
    token = CapabilityToken(http=HttpCapability(allowed_domains=["site-a.com", "site-b.com"]))
    
    def mock_gethostbyname(domain: str) -> str:
        if domain == "site-a.com":
            return "8.8.8.8"
        elif domain == "site-b.com":
            return "9.9.9.9"
        return "127.0.0.1"
        
    monkeypatch.setattr("socket.gethostbyname", mock_gethostbyname)
    
    import urllib3.util.connection
    def mock_create_connection(address: tuple[str, int], *args: Any, **kwargs: Any) -> Any:
        raise Exception(f"Connected to {address[0]}")
        
    monkeypatch.setattr("urllib3.util.connection.create_connection", mock_create_connection)
    
    def fetch(domain: str) -> str:
        res = tool.execute(token, {"method": "GET", "url": f"http://{domain}/"}, rate_limiter=RateLimiter())
        return res.error or ""
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(fetch, "site-a.com")
        f2 = executor.submit(fetch, "site-b.com")
        
        err1 = f1.result()
        err2 = f2.result()
        
    assert "Connected to 8.8.8.8" in err1
    assert "Connected to 9.9.9.9" in err2
