from replay.passive_replay import PassiveReplay
from pprint import pprint

def run(trace_path: str) -> None:
    print(f"Running Passive Replay for {trace_path}...")
    replay = PassiveReplay(trace_path)
    for step_result in replay.run():
        pprint(step_result)
