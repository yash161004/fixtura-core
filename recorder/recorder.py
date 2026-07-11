import json
import threading
import zstandard as zstd
from typing import Dict, Any, Union
from pathlib import Path
from recorder.sanitizer import Sanitizer

class ExecutionRecorder:
    def __init__(self, trace_file: Union[str, Path], parent_trace_id: str | None = None, divergence_step_id: str | None = None) -> None:
        self.trace_file = Path(trace_file)
        self.sanitizer = Sanitizer()
        self._lock = threading.Lock()
        self._step_counter = 1
        
        if parent_trace_id and divergence_step_id:
            header = {
                "event_type": "trace_header",
                "parent_trace_id": parent_trace_id,
                "divergence_step_id": divergence_step_id
            }
            sanitized = self.sanitizer.sanitize(header)
            line = json.dumps(sanitized) + "\n"
            cctx = zstd.ZstdCompressor()
            with open(self.trace_file, "ab") as f:
                f.write(cctx.compress(line.encode("utf-8")))

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
