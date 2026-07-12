import re
from typing import Any, Dict, List, Union

REDACTED = "[REDACTED]"
TRUNCATED_SUFFIX = "...[TRUNCATED]"

SENSITIVE_KEYS = {"authorization", "api_key", "password", "secret", "bearer", "cookie"}

PATTERNS = [
    re.compile(r'Bearer\s+[A-Za-z0-9\-\.\_~+/]+'),
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),
    re.compile(r'sk_live_[a-zA-Z0-9]+'),
    re.compile(r'ey[a-zA-Z0-9_-]+\.ey[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'[A-Za-z0-9-_]{40,}')
]

class Sanitizer:
    def _redact_patterns(self, text: str) -> str:
        for pattern in PATTERNS:
            text = pattern.sub(REDACTED, text)
        return text

    def _truncate(self, text: str, max_bytes: int) -> str:
        encoded = text.encode("utf-8")
        if len(encoded) > max_bytes:
            sliced = encoded[:max_bytes]
            # Decode with errors="ignore" to safely drop partial multi-byte codepoints
            decoded = sliced.decode("utf-8", errors="ignore")
            return decoded + TRUNCATED_SUFFIX
        return text

    def _sanitize_value(self, value: Any, is_sensitive_key: bool, limit_bytes: int) -> Any:
        # Pass 1: Recursive Traversal
        if isinstance(value, dict):
            result: Dict[str, Any] = {}
            for k, v in value.items():
                is_sens = isinstance(k, str) and k.lower() in SENSITIVE_KEYS
                # Nested fields always fall back to the default 50KB limit
                result[k] = self._sanitize_value(v, is_sens, 50 * 1024)
            return result
        elif isinstance(value, list):
            return [self._sanitize_value(item, False, limit_bytes) for item in value]
        elif isinstance(value, str):
            # Pass 2: Key-based Redaction
            if is_sensitive_key:
                return REDACTED
            
            # Pass 3: Pattern-based Redaction
            redacted = self._redact_patterns(value)
            
            # Pass 4: Truncation
            return self._truncate(redacted, limit_bytes)
        return value

    def sanitize(self, event: Dict[str, Any]) -> Dict[str, Any]:
        is_llm_call = event.get("event_type") == "llm_call"
        result: Dict[str, Any] = {}
        
        for k, v in event.items():
            is_sensitive = isinstance(k, str) and k.lower() in SENSITIVE_KEYS
            limit_bytes = 50 * 1024
            
            # Preserve strict top-level limits for llm_call
            if is_llm_call and k == "prompt":
                limit_bytes = 20 * 1024
            elif is_llm_call and k == "completion":
                limit_bytes = 50 * 1024
                
            result[k] = self._sanitize_value(v, is_sensitive, limit_bytes)
            
        return result
