from replay.step_inspector import StepInspector
from pprint import pprint

def run(trace_path: str):
    print(f"Running Step Inspector for {trace_path}...")
    inspector = StepInspector(trace_path)
    step = 1
    while inspector.advance():
        current = inspector.current_step()
        print(f"\n--- Paused at Step {step} ---")
        pprint(current)
        input("Press Enter to continue to next step...")
        step += 1
    print("\nReached end of trace.")
