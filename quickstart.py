import os
from pprint import pprint
from cli.record import run as record_run
from cli.replay import run as replay_run
from replay.step_inspector import StepInspector

def main() -> None:
    print("Fixtura Quickstart")
    print("==================")
    
    trace_path = "quickstart_example.trace"
    
    # 1. Record a short trace
    print(f"\n[1/3] Recording a sample agent run to '{trace_path}'...")
    record_run(trace_path)
    
    # 2. Replay passively
    print("\n[2/3] Replaying the recorded trace (no live calls made)...")
    replay_run(trace_path)
    
    # 3. Print a brief step-by-step summary
    print("\n[3/3] Inspecting the replayed trace summary...")
    inspector = StepInspector(trace_path)
    step = 1
    while inspector.advance():
        current = inspector.current_step()
        print(f"\n--- Step {step} ---")
        # Reuse pprint to ensure we reuse existing view/inspect formatting logic
        pprint(current)
        step += 1
        
    print(f"\nDone! Trace saved to {os.path.abspath(trace_path)}")

if __name__ == "__main__":
    main()
