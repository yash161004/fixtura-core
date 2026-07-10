import sys
import re
from pathlib import Path
from typing import Union, Dict, Any

from openeval.models import AgentTrace, TraceStep
from recorder.trace_reader import TraceReader

def extract_step_id(step_id_str: str) -> int:
    digits = re.sub(r'\D', '', step_id_str)
    if not digits:
        raise ValueError(f"Could not extract integer from step_id: {step_id_str}")
    return int(digits)

def trace_to_agent_trace(
    trace_path: Union[str, Path], 
    task_id: str, 
    input_text: str, 
    final_output: str, 
    actual_state: dict[str, Any],
    metadata: dict[str, Any] | None = None
) -> AgentTrace:
    """
    Converts a Fixtura .trace file into an OpenEval AgentTrace.
    Since Fixtura traces do not currently wrap events with top-level execution metadata, 
    task_id, input, final_output, and actual_state must be passed explicitly.
    """
    if metadata is None:
        metadata = {}
        
    reader = TraceReader(trace_path)
    steps = []
    seen_step_ids = set()
    
    for event in reader.read_events():
        raw_step_id = event["step_id"]
        step_id_int = extract_step_id(raw_step_id)
        
        if step_id_int in seen_step_ids:
            raise ValueError(f"Step ID collision after int conversion: {raw_step_id} -> {step_id_int}")
        seen_step_ids.add(step_id_int)
        
        event_type = event.get("event_type")
        timestamp = event["timestamp"]
        
        if event_type == "llm_call":
            # Map llm_call -> thought
            prompt = event.get("prompt", "")
            completion = event.get("completion", "")
            content = f"PROMPT:\n{prompt}\n\nCOMPLETION:\n{completion}"
            
            step = TraceStep(
                step_id=step_id_int,
                type="thought",
                content=content,
                tool_name=None,
                tool_args=None,
                tool_result=None,
                timestamp=timestamp,
                error=None
            )
            steps.append(step)
            
        elif event_type == "tool_call":
            decision = event.get("permission_decision")
            tool_name = event.get("tool_name")
            arguments = event.get("arguments")
            
            if decision == "allowed":
                step = TraceStep(
                    step_id=step_id_int,
                    type="tool_call",
                    content="",
                    tool_name=tool_name,
                    tool_args=arguments,
                    tool_result=event.get("response"),
                    timestamp=timestamp,
                    error=None
                )
                steps.append(step)
            elif decision == "denied":
                # Denied -> tool_name = None (avoids metrics), error = permission_reason
                reason = event.get("permission_reason", "Denied")
                human_note = f"ATTEMPTED TOOL: {tool_name}\nATTEMPTED ARGS: {arguments}"
                
                step = TraceStep(
                    step_id=step_id_int,
                    type="tool_call",
                    content=human_note,
                    tool_name=None,
                    tool_args=None,
                    tool_result=None,
                    timestamp=timestamp,
                    error=reason
                )
                steps.append(step)
    
    return AgentTrace(
        task_id=task_id,
        input=input_text,
        steps=steps,
        final_output=final_output,
        actual_state=actual_state,
        metadata=metadata
    )
