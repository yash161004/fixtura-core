import sys
import unittest.mock
from pathlib import Path
from cli.main import replay

def intercept(*args, **kwargs):
    raise AssertionError(f"Intercepted real call! args={args}, kwargs={kwargs}")

def main():
    trace_file = "at5.trace" if Path("at5.trace").exists() else "test.trace"
    if not Path(trace_file).exists():
        print(f"Creating a trace file {trace_file} first...")
        from cli.main import record
        record.run(trace_file)

    # Monkeypatch the tools directly where they make external calls
    with unittest.mock.patch('sqlite3.connect', side_effect=intercept) as mock_sql, \
         unittest.mock.patch('requests.Session.request', side_effect=intercept) as mock_req:
         
         # The replay function uses trace_reader to read the file, which uses builtins.open
         # so we have to allow reading the trace file itself, but block other opens.
         original_open = open
         def safe_open(file, *args, **kwargs):
             if str(file).endswith('.trace'):
                 return original_open(file, *args, **kwargs)
             raise AssertionError(f"Intercepted real file access: {file}")
         
         with unittest.mock.patch('builtins.open', side_effect=safe_open):
             try:
                 replay.run(trace_file)
                 print("\nAT2 True Verification Passed: No real calls were intercepted.")
             except AssertionError as e:
                 print(f"\nAT2 True Verification Failed: {e}")
                 sys.exit(1)

if __name__ == '__main__':
    main()
