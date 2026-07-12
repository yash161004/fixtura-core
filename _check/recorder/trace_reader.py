import io
import json
import zstandard as zstd
from typing import Dict, Any, Union, Iterator, Set
from pathlib import Path

class TraceValidationError(Exception):
    pass

class MissingParentTraceError(Exception):
    pass

def resolve_trace_path(trace_id: str, base_dir: Path) -> Path:
    """
    Seam for resolving trace IDs to physical files. 
    Currently assumes same-directory storage, but abstracting this 
    allows swapping the storage backend later without breaking lineage logic.
    """
    return base_dir / f"{trace_id}.trace"

class TraceReader:
    """
    The only sanctioned way to read a .trace file.
    Reads zstd-compressed JSONL with multiple independent frames.
    """
    def __init__(self, trace_file: Union[str, Path]) -> None:
        self.trace_file = Path(trace_file)
        
    def _validate_event(self, event: Dict[str, Any], seen_ids: Set[str]) -> None:
        event_type = event.get("event_type")
        if event_type not in ("llm_call", "tool_call", "trace_header"):
            raise TraceValidationError(f"Invalid event_type: {event_type}")
            
        if event_type == "trace_header":
            required = ["parent_trace_id", "divergence_step_id"]
            for req in required:
                if req not in event:
                    raise TraceValidationError(f"trace_header missing required field: {req}")
            return

        if "step_id" not in event:
            raise TraceValidationError("Missing required field: step_id")
        if "timestamp" not in event:
            raise TraceValidationError("Missing required field: timestamp")
            
        step_id = event["step_id"]
        if step_id in seen_ids:
            raise TraceValidationError(f"Duplicate step_id detected: {step_id}")
        seen_ids.add(step_id)
            
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
            if decision not in ("allowed", "denied", "validation_error"):
                raise TraceValidationError(f"Invalid permission_decision: {decision}")
                
            if decision in ("denied", "validation_error"):
                if "permission_reason" not in event or event["permission_reason"] is None:
                    # Backward compatibility for pre-1.0.4 traces
                    event["permission_reason"] = "Unknown denial reason (legacy trace)"
                elif not isinstance(event["permission_reason"], str):
                    raise TraceValidationError(f"permission_reason must be a string when permission_decision is {decision}")
                
                if "response" not in event or event.get("response") is not None:
                    raise TraceValidationError(f"response must be null when permission_decision is {decision}")
            elif decision == "allowed":
                if "response" not in event:
                    raise TraceValidationError("response is required when permission_decision is allowed")

    def read_events(self) -> Iterator[Dict[str, Any]]:
        if not self.trace_file.exists():
            return
            
        seen_ids: Set[str] = set()
        dctx = zstd.ZstdDecompressor()
        
        # We need to potentially buffer the first event to check for trace_header
        def _read_raw_events() -> Iterator[Dict[str, Any]]:
            with open(self.trace_file, "rb") as f:
                with dctx.stream_reader(f, read_across_frames=True) as reader:
                    text_stream = io.TextIOWrapper(reader, encoding="utf-8")
                    for line in text_stream:
                        line = line.strip()
                        if line:
                            event = json.loads(line)
                            self._validate_event(event, seen_ids)
                            yield event
        
        raw_events = _read_raw_events()
        
        try:
            first_event = next(raw_events)
        except StopIteration:
            return
            
        if first_event.get("event_type") == "trace_header":
            parent_id = first_event["parent_trace_id"]
            divergence_id = first_event["divergence_step_id"]
            
            parent_path = resolve_trace_path(parent_id, self.trace_file.parent)
            if not parent_path.exists():
                raise MissingParentTraceError(f"Cannot resolve parent trace: {parent_id}")
                
            parent_reader = TraceReader(parent_path)
            # Yield from parent up to divergence_step_id
            for p_event in parent_reader.read_events():
                seen_ids.add(p_event["step_id"])
                yield p_event
                if p_event.get("step_id") == divergence_id:
                    break
        else:
            yield first_event
            
        for event in raw_events:
            yield event
