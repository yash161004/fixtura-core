import sys
from tools import html_viewer

def run(trace_path: str) -> None:
    # Hijack sys.argv so argparse in html_viewer.main() works
    sys.argv = ["fixtura html-view", trace_path]
    html_viewer.main()
