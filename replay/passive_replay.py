from typing import Dict, Any, Union, Iterator
from pathlib import Path
from recorder.trace_reader import TraceReader

class PassiveReplay:
    """
    Executes a Passive Replay of a trace file.
    No live tool calls, LLM requests, or permission re-evaluations are performed.
    """
    def __init__(self, trace_file: Union[str, Path]) -> None:
        self.trace_file = Path(trace_file)
        self.reader = TraceReader(self.trace_file)

    def run(self) -> Iterator[Dict[str, Any]]:
        """
        Consumes events strictly in recorded order.
        Yields recorded data without re-invoking external resources.
        """
        for event in self.reader.read_events():
            event_type = event["event_type"]
            
            if event_type == "llm_call":
                yield self._handle_llm_call(event)
            elif event_type == "tool_call":
                yield self._handle_tool_call(event)

    def _handle_llm_call(self, event: Dict[str, Any]) -> Dict[str, Any]:
        # Reconstruct exactly as recorded
        return {"status": "success", "result": event["completion"]}

    def _handle_tool_call(self, event: Dict[str, Any]) -> Dict[str, Any]:
        # Reconstruct execution state
        decision = event["permission_decision"]
        
        if decision == "denied":
            # Reproduce permission denial locally
            reason = event["permission_reason"]
            return {"status": "denied", "reason": reason}
            
        exception = event.get("exception")
        if exception is not None:
            # Reproduce the exact recorded exception to prevent silent swallowing
            raise RuntimeError(f"Recorded tool_call failed: {exception}")
            
        return {"status": "success", "result": event["response"]}
