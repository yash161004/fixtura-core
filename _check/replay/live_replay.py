import time
from typing import Callable, Any, Dict, List, Optional
from recorder.trace_reader import TraceReader
from recorder.recorder import ExecutionRecorder
from security.permission_engine import CapabilityToken
from security.rate_limiter import RateLimiter
from tools.base_tool import BaseTool

class LiveReplayRuntime:
    def __init__(
        self,
        parent_trace_path: str,
        branch_trace_path: str,
        divergence_step_id: str,
        agent_callable: Callable[[List[Dict[str, Any]], str], List[Dict[str, Any]]],
        capability_token: CapabilityToken,
        rate_limiter: RateLimiter,
        tools: Dict[str, BaseTool]
    ):
        self.parent_trace_path = parent_trace_path
        self.branch_trace_path = branch_trace_path
        self.divergence_step_id = divergence_step_id
        self.agent_callable = agent_callable
        self.capability_token = capability_token
        self.rate_limiter = rate_limiter
        self.tools = tools
        
    def run(self, new_prompt: str) -> None:
        # 1. Build context from parent trace
        reader = TraceReader(self.parent_trace_path)
        context_events = []
        for event in reader.read_events():
            context_events.append(event)
            if event.get("step_id") == self.divergence_step_id:
                break
                
        # 2. Setup recorder for the new branch
        # This will write the trace_header automatically
        recorder = ExecutionRecorder(
            self.branch_trace_path,
            parent_trace_id=reader.trace_file.stem,
            divergence_step_id=self.divergence_step_id
        )
        
        # 3. Call the agent
        # The agent callable returns a list of "intent" events.
        # - {"type": "llm_call", ...fields...}
        # - {"type": "tool_call_request", "tool_name": "...", "arguments": {...}}
        intents = self.agent_callable(context_events, new_prompt)
        
        for intent in intents:
            if intent["type"] == "llm_call":
                # Remove internal type marker before recording
                event = dict(intent)
                event.pop("type")
                event["event_type"] = "llm_call"
                recorder.record_event(event)
                
            elif intent["type"] == "tool_call_request":
                tool_name = str(intent["tool_name"])
                arguments = dict(intent["arguments"])
                
                tool = self.tools.get(tool_name)
                start_time = time.time()
                
                res_outcome: str = "validation_error"
                res_error: Optional[str] = None
                res_reason: Optional[str] = None
                res_result: Optional[Any] = None
                
                if tool is None:
                    # Tool not found
                    res_outcome = "validation_error"
                    res_error = f"Tool {tool_name} not found."
                else:
                    res = tool.execute(self.capability_token, arguments, self.rate_limiter)
                    res_outcome = res.outcome
                    res_error = res.error
                    res_reason = res.reason
                    res_result = res.result
                    
                latency_ms = int((time.time() - start_time) * 1000)
                
                recorder.record_event({
                    "event_type": "tool_call",
                    "timestamp": time.time() * 1000,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "permission_decision": "allowed" if res_outcome not in ("permission_denied", "validation_error") else "denied",
                    "permission_reason": res_reason if res_outcome == "permission_denied" else (res_error if res_outcome == "validation_error" else None),
                    "rate_limit_decision": "rate_limited" if res_outcome == "rate_limited" else ("circuit_broken" if res_outcome == "circuit_broken" else "allowed"),
                    "rate_limit_reason": res_reason if res_outcome in ("rate_limited", "circuit_broken") else None,
                    "response": res_result,
                    "latency_ms": latency_ms
                })
