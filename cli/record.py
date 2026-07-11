import os
import sqlite3

from security.permission_engine import CapabilityToken
from security.rate_limiter import RateLimiter
from recorder.recorder import ExecutionRecorder
from tools.filesystem_tool import FilesystemTool
from tools.sqlite_tool import SqliteTool
from tools.http_tool import HttpTool

def run(trace_path: str) -> None:
    print(f"Recording canonical test trace to {trace_path}...")
    
    if os.path.exists(trace_path):
        os.remove(trace_path)
        
    recorder = ExecutionRecorder(trace_path)
    
    token = CapabilityToken()
    token.filesystem.read = [os.getcwd()]
    token.filesystem.write = [os.getcwd()]
    token.http.allowed_domains = ["example.com"]
    # No DB permissions given
    
    rate_limiter = RateLimiter()
    
    fs_tool = FilesystemTool(sandbox_root=os.getcwd())
    
    db_path = "test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
    db_tool = SqliteTool(db_path=db_path)
    
    http_tool = HttpTool()
    
    # 1. LLM Step
    recorder.record_event({
        "event_type": "llm_call",
        "timestamp": 100.0,
        "prompt": "Read the local file",
        "completion": "I'll use filesystem tool",
        "provider": "test",
        "model": "test",
        "input_tokens": 10,
        "output_tokens": 10,
        "finish_reason": "stop",
        "latency_ms": 100
    })
    
    # 2. FS Tool (Should be allowed)
    with open("test.txt", "w") as f:
        f.write("test_content secret-sk-12345678901234567890")
    
    args = {"operation": "read", "path": os.path.abspath("test.txt")}
    res = fs_tool.execute(token, args, rate_limiter=rate_limiter)
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 200.0,
        "tool_name": "filesystem_tool",
        "arguments": args,
        "permission_decision": "allowed" if res.outcome not in ("permission_denied", "validation_error") else "denied",
        "permission_reason": res.reason if res.outcome == "permission_denied" else (res.error if res.outcome == "validation_error" else None),
        "rate_limit_decision": "rate_limited" if res.outcome == "rate_limited" else ("circuit_broken" if res.outcome == "circuit_broken" else "allowed"),
        "rate_limit_reason": res.reason if res.outcome in ("rate_limited", "circuit_broken") else None,
        "response": res.result,
        "latency_ms": 50
    })
        
    # 3. DB Tool (Should be denied)
    args = {"operation": "read", "query": "SELECT * FROM test"}
    res = db_tool.execute(token, args, rate_limiter=rate_limiter)
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 300.0,
        "tool_name": "sqlite_tool",
        "arguments": args,
        "permission_decision": "allowed" if res.outcome not in ("permission_denied", "validation_error") else "denied",
        "permission_reason": res.reason if res.outcome == "permission_denied" else (res.error if res.outcome == "validation_error" else None),
        "rate_limit_decision": "rate_limited" if res.outcome == "rate_limited" else ("circuit_broken" if res.outcome == "circuit_broken" else "allowed"),
        "rate_limit_reason": res.reason if res.outcome in ("rate_limited", "circuit_broken") else None,
        "response": res.result,
        "latency_ms": 50
    })

    # 4. HTTP Tool (Should be denied because we pass a disallowed URL to trigger another denial, 
    # or we can pass an allowed one. The prompt says "at least one allowed and one denied". 
    # I'll pass a denied one to match the OpenEval adapter test expectation of missing tools)
    args = {"url": "http://disallowed.com"}
    res = http_tool.execute(token, args, rate_limiter=rate_limiter)
    recorder.record_event({
        "event_type": "tool_call",
        "timestamp": 400.0,
        "tool_name": "http_tool",
        "arguments": args,
        "permission_decision": "allowed" if res.outcome not in ("permission_denied", "validation_error") else "denied",
        "permission_reason": res.reason if res.outcome == "permission_denied" else (res.error if res.outcome == "validation_error" else None),
        "rate_limit_decision": "rate_limited" if res.outcome == "rate_limited" else ("circuit_broken" if res.outcome == "circuit_broken" else "allowed"),
        "rate_limit_reason": res.reason if res.outcome in ("rate_limited", "circuit_broken") else None,
        "response": res.result,
        "latency_ms": 50
    })
    
    print("Trace recording complete!")
