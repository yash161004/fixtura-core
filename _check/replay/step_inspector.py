from typing import Dict, Any, Union, Iterator
from pathlib import Path
from replay.passive_replay import PassiveReplay

class StepInspector:
    """
    Wraps PassiveReplay for Step Inspection.
    Pauses after every event, exposing the raw event dictionary strictly read-only.
    """
    def __init__(self, trace_file: Union[str, Path]) -> None:
        self._passive_replay = PassiveReplay(trace_file)
        self._event_iterator: Iterator[Dict[str, Any]] = self._passive_replay.reader.read_events()
        self._current_step: Dict[str, Any] = {}

    def advance(self) -> bool:
        """
        Advances the trace by exactly one step.
        Returns True if a step was loaded, False if EOF is reached.
        """
        try:
            # Yields exactly one event, simulating a breakpoint pause
            self._current_step = next(self._event_iterator)
            return True
        except StopIteration:
            self._current_step = {}
            return False

    def current_step(self) -> Dict[str, Any]:
        """
        Exposes the current event payload.
        Returns a copy to enforce strict read-only guarantees (no mutation).
        """
        return self._current_step.copy()
