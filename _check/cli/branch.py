import os
import sqlite3
from typing import List, Dict, Any

from security.permission_engine import CapabilityToken
from security.rate_limiter import RateLimiter
from tools.filesystem_tool import FilesystemTool
from tools.sqlite_tool import SqliteTool
from tools.http_tool import HttpTool
from replay.live_replay import LiveReplayRuntime

def dummy_agent_callable(context_events: List[Dict[str, Any]], new_prompt: str) -> List[Dict[str, Any]]:
    """
    A dummy agent that simply outputs a pre-programmed thought and tool call 
    based on the new_prompt, to prove the branching pipeline works.
    """
    return [
        {
            "type": "llm_call",
            "timestamp": 0.0, # replaced by recorder
            "prompt": new_prompt,
            "completion": f"I will now process the new branch prompt: {new_prompt}",
            "provider": "dummy",
            "model": "dummy-branch",
            "input_tokens": 10,
            "output_tokens": 20,
            "finish_reason": "stop",
            "latency_ms": 150
        },
        {
            "type": "tool_call_request",
            "tool_name": "filesystem_tool",
            "arguments": {
                "operation": "write",
                "path": os.path.abspath("branch_output.txt"),
                "content": f"Branched Output: {new_prompt}"
            }
        }
    ]

def run(parent_trace: str, branch_trace: str, divergence_step: str, prompt: str) -> None:
    print(f"Branching trace {parent_trace} at {divergence_step} -> {branch_trace}...")
    
    if os.path.exists(branch_trace):
        os.remove(branch_trace)
        
    token = CapabilityToken()
    token.filesystem.read = [os.getcwd()]
    token.filesystem.write = [os.getcwd()]
    token.http.allowed_domains = ["example.com"]
    # No DB permissions given to verify security
    
    rate_limiter = RateLimiter()
    
    tools = {
        "filesystem_tool": FilesystemTool(sandbox_root=os.getcwd()),
        "sqlite_tool": SqliteTool(db_path="test.db"),
        "http_tool": HttpTool()
    }
    
    db_path = "test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
        
    runtime = LiveReplayRuntime(
        parent_trace_path=parent_trace,
        branch_trace_path=branch_trace,
        divergence_step_id=divergence_step,
        agent_callable=dummy_agent_callable,
        capability_token=token,
        rate_limiter=rate_limiter,
        tools=tools
    )
    
    runtime.run(new_prompt=prompt)
    print("Branch trace recording complete!")
