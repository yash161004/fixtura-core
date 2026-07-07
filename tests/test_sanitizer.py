import pytest
from recorder.sanitizer import Sanitizer

def test_nested_secret() -> None:
    sanitizer = Sanitizer()
    event = {
        "event_type": "tool_call",
        "arguments": {
            "query": "SELECT * FROM users",
            "metadata": {
                "user": {
                    "profile": {
                        "notes": "secret-sk-12345678901234567890",
                        "password": "my_super_secret_password"
                    }
                }
            }
        }
    }
    
    sanitized = sanitizer.sanitize(event)
    
    profile = sanitized["arguments"]["metadata"]["user"]["profile"]
    
    # 1. Pattern-based redaction (nested)
    assert profile["notes"] == "secret-[REDACTED]"
    
    # 2. Key-based redaction (nested)
    assert profile["password"] == "[REDACTED]"

def test_redact_then_truncate_boundary() -> None:
    sanitizer = Sanitizer()
    secret = "sk-12345678901234567890"  # 23 bytes
    
    # Case 1: Post-redaction length < 51,200 bytes
    prefix1 = "*" * (51210 - len(secret))
    event1 = {"event_type": "tool_call", "arguments": {"blob": prefix1 + secret}}
    san = sanitizer.sanitize(event1)
    
    assert "[REDACTED]" in san["arguments"]["blob"]
    assert "sk-" not in san["arguments"]["blob"]
    assert "...[TRUNCATED]" not in san["arguments"]["blob"] # Should not truncate!
    
    # Case 2: Post-redaction length > 51,200 bytes, secret is truncated entirely
    prefix2 = "*" * 51210
    event2 = {"event_type": "tool_call", "arguments": {"blob": prefix2 + secret}}
    san2 = sanitizer.sanitize(event2)
    
    assert "sk-" not in san2["arguments"]["blob"]
    assert "...[TRUNCATED]" in san2["arguments"]["blob"]
    assert "[REDACTED]" not in san2["arguments"]["blob"] # Sliced off
    
    # Case 3: Post-redaction length > 51,200 bytes, [REDACTED] is partially cut
    prefix3 = "*" * 51195
    event3 = {"event_type": "tool_call", "arguments": {"blob": prefix3 + secret}}
    san3 = sanitizer.sanitize(event3)
    
    assert "sk-" not in san3["arguments"]["blob"]
    # The first 5 chars of "[REDACTED]" survive
    assert san3["arguments"]["blob"].endswith("[REDA...[TRUNCATED]")

def test_multibyte_truncation() -> None:
    sanitizer = Sanitizer()
    
    # '€' is 3 bytes. We put it at exactly byte boundary 51,199 to 51,201.
    # The 51,200 byte slice will grab the first byte of '€', leaving an invalid sequence.
    # It must safely drop the partial byte.
    s = "*" * 51199 + "€"
    assert len(s.encode("utf-8")) == 51202
    
    event = {"event_type": "tool_call", "arguments": {"data": s}}
    sanitized = sanitizer.sanitize(event)
    
    # Should safely drop the partial codepoint, leaving 51199 *'s
    assert sanitized["arguments"]["data"] == ("*" * 51199) + "...[TRUNCATED]"

def test_llm_call_specific_limits() -> None:
    sanitizer = Sanitizer()
    
    # llm_call prompt gets 20KB limit, completion gets 50KB limit
    s20k = "*" * 20485
    s50k = "*" * 51205
    
    event = {
        "event_type": "llm_call",
        "prompt": s20k,
        "completion": s50k,
        "other": s50k
    }
    
    sanitized = sanitizer.sanitize(event)
    
    assert len(sanitized["prompt"]) == 20480 + len("...[TRUNCATED]")
    assert len(sanitized["completion"]) == 51200 + len("...[TRUNCATED]")
    assert len(sanitized["other"]) == 51200 + len("...[TRUNCATED]") # default limit
