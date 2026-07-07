import json
import threading
import zstandard as zstd
from typing import Dict, Any, Union
from pathlib import Path
from recorder.sanitizer import Sanitizer

class ExecutionRecorder:
    def __init__(self, trace_file: Union[str, Path]) -> None:
        self.trace_file = Path(trace_file)
        self.sanitizer = Sanitizer()
        self._lock = threading.Lock()
        self._step_counter = 1

    def record_event(self, event: Dict[str, Any]) -> None:
        """
        Sanitizes and records a single event to the .trace file.
        No code path is allowed to bypass the sanitizer per TRACE_FORMAT_SPEC.md.
        """
        with self._lock:
            # Overwrite any incoming step_id with our monotonic generator
            event["step_id"] = f"step-{self._step_counter:06d}"
            self._step_counter += 1
            
            # Pass through the sanitizer pipeline
            sanitized_event = self.sanitizer.sanitize(event)
            
            # Serialize to JSONL string
            line = json.dumps(sanitized_event) + "\n"
            
            # Instantiate compressor locally to avoid shared mutable state
            cctx = zstd.ZstdCompressor()
            compressed_frame = cctx.compress(line.encode("utf-8"))
            
            with open(self.trace_file, "ab") as f:
                f.write(compressed_frame)
