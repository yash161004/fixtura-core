import os
from pprint import pprint

from tools.openeval_adapter import trace_to_agent_trace
from openeval.runner import run_eval
from openeval.models import EvalTestCase
from openeval.metrics import ToolSelectionAccuracy, ArgumentCorrectness, StepEfficiency, GoalCompletionRate

def run(trace_path: str) -> None:
    print(f"Scoring {trace_path} via OpenEval adapter...")
    metrics = [
        ToolSelectionAccuracy(),
        ArgumentCorrectness(),
        StepEfficiency(),
        GoalCompletionRate()
    ]
    
    # We match the test case against the fixture agent built in cli.record
    tc = EvalTestCase(
        task_id="canonical-task",
        input="Do stuff",
        expected_tool_calls=[
            {"tool": "filesystem_tool", "args": {"operation": "read", "path": "wrong_path.txt"}},
            {"tool": "sqlite_tool", "args": {"operation": "read", "query": "SELECT * FROM test"}},
            {"tool": "http_tool", "args": {"url": "http://disallowed.com"}}
        ],
        expected_final_state={},
        expected_output_contains=[],
        max_steps=5,
        timeout_seconds=10.0
    )
    
    trace = trace_to_agent_trace(
        trace_path=trace_path,
        task_id="canonical-task",
        input_text="Do stuff",
        final_output="Done",
        actual_state={}
    )
    
    res = run_eval(trace, tc, metrics)
    pprint(res)
