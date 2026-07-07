import io
import json
import zstandard as zstd
from typing import Dict, Any, Union, Iterator, Set
from pathlib import Path

class TraceValidationError(Exception):
    pass

class TraceReader:
    """
    The only sanctioned way to read a .trace file.
    Reads zstd-compressed JSONL with multiple independent frames.
    """
    def __init__(self, trace_file: Union[str, Path]) -> None:
        self.trace_file = Path(trace_file)
        
    def _validate_event(self, event: Dict[str, Any], seen_ids: Set[str]) -> None:
        if "step_id" not in event:
            raise TraceValidationError("Missing required field: step_id")
        if "timestamp" not in event:
            raise TraceValidationError("Missing required field: timestamp")
            
        step_id = event["step_id"]
        if step_id in seen_ids:
            raise TraceValidationError(f"Duplicate step_id detected: {step_id}")
        seen_ids.add(step_id)
        
        event_type = event.get("event_type")
        if event_type not in ("llm_call", "tool_call"):
            raise TraceValidationError(f"Invalid event_type: {event_type}")
            
        if event_type == "llm_call":
            required = ["prompt", "completion", "provider", "model", "input_tokens", 
                        "output_tokens", "finish_reason", "latency_ms"]
            for req in required:
                if req not in event:
                    raise TraceValidationError(f"llm_call missing required field: {req}")
                    
        elif event_type == "tool_call":
            required = ["tool_name", "arguments", "permission_decision", "latency_ms"]
            for req in required:
                if req not in event:
                    raise TraceValidationError(f"tool_call missing required field: {req}")
                    
            decision = event["permission_decision"]
            if decision not in ("allowed", "denied"):
                raise TraceValidationError(f"Invalid permission_decision: {decision}")
                
            if decision == "denied":
                if "permission_reason" not in event:
                    raise TraceValidationError("permission_reason required when permission_decision is denied")
                if "response" not in event or event.get("response") is not None:
                    raise TraceValidationError("response must be null when permission_decision is denied")
            elif decision == "allowed":
                if "response" not in event:
                    raise TraceValidationError("response is required when permission_decision is allowed")

    def read_events(self) -> Iterator[Dict[str, Any]]:
        if not self.trace_file.exists():
            return
            
        seen_ids: Set[str] = set()
        dctx = zstd.ZstdDecompressor()
        with open(self.trace_file, "rb") as f:
            # read_across_frames=True is CRITICAL for concatenated .trace files
            with dctx.stream_reader(f, read_across_frames=True) as reader:
                # Wrap the raw byte stream in a TextIOWrapper for line iteration
                text_stream = io.TextIOWrapper(reader, encoding="utf-8")
                for line in text_stream:
                    line = line.strip()
                    if line:
                        event = json.loads(line)
                        self._validate_event(event, seen_ids)
                        yield event
