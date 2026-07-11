import argparse
import sys

from cli import record, replay, inspect, view, eval, html_view, branch

def main() -> None:
    parser = argparse.ArgumentParser(description="Fixtura CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Record
    parser_record = subparsers.add_parser("record", help="Record a trace using the canonical test agent")
    parser_record.add_argument("trace_file", help="Path to output trace file")
    
    # Replay
    parser_replay = subparsers.add_parser("replay", help="Passively replay a trace")
    parser_replay.add_argument("trace_file", help="Path to input trace file")
    
    # Inspect
    parser_inspect = subparsers.add_parser("inspect", help="Step-inspect a trace interactively")
    parser_inspect.add_argument("trace_file", help="Path to input trace file")
    
    # Branch
    parser_branch = subparsers.add_parser("branch", help="Create a live branch from an existing trace")
    parser_branch.add_argument("parent_trace", help="Path to input parent trace file")
    parser_branch.add_argument("branch_trace", help="Path to output branch trace file")
    parser_branch.add_argument("divergence_step", help="Step ID to diverge at")
    parser_branch.add_argument("prompt", help="New prompt for the diverged branch")
    
    # View
    parser_view = subparsers.add_parser("view", help="View a trace summary")
    parser_view.add_argument("trace_file", help="Path to input trace file")
    
    # Eval
    parser_eval = subparsers.add_parser("eval", help="Score a trace via OpenEval adapter")
    parser_eval.add_argument("trace_file", help="Path to input trace file")
    
    # HTML View
    parser_html_view = subparsers.add_parser("html-view", help="View a trace summary in HTML format")
    parser_html_view.add_argument("trace_file", help="Path to input trace file")

    args = parser.parse_args()
    
    if args.command == "record":
        record.run(args.trace_file)
    elif args.command == "replay":
        replay.run(args.trace_file)
    elif args.command == "inspect":
        inspect.run(args.trace_file)
    elif args.command == "branch":
        branch.run(args.parent_trace, args.branch_trace, args.divergence_step, args.prompt)
    elif args.command == "view":
        view.run(args.trace_file)
    elif args.command == "eval":
        eval.run(args.trace_file)
    elif args.command == "html-view":
        html_view.run(args.trace_file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
