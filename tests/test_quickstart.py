import subprocess
import os

def test_quickstart_runs_successfully() -> None:
    """
    Test that the quickstart script runs end-to-end without error,
    exits with code 0, and outputs evidence of record, replay, 
    and permission decisions.
    """
    result = subprocess.run(
        ["python", "quickstart.py"], 
        capture_output=True, 
        text=True
    )
    
    assert result.returncode == 0, f"quickstart.py failed with output:\n{result.stderr}"
    
    output = result.stdout
    
    # Check for evidence of record
    assert "Recording a sample agent run" in output
    
    # Check for evidence of replay
    assert "Replaying the recorded trace" in output
    
    # Check for evidence of permission decisions
    assert "permission_decision" in output
    assert "allowed" in output
    assert "denied" in output
    
    # Check for evidence of redaction
    assert "[REDACTED]" in output
