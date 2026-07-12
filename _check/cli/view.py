import sys
from tools import viewer

def run(trace_path: str) -> None:
    # Hijack sys.argv so argparse in viewer.main() works
    sys.argv = ["fixtura view", trace_path]
    viewer.main()
