import argparse
import sys

from cli import record, replay, inspect, view, eval

def main():
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
    
    # View
    parser_view = subparsers.add_parser("view", help="View a trace summary")
    parser_view.add_argument("trace_file", help="Path to input trace file")
    
    # Eval
    parser_eval = subparsers.add_parser("eval", help="Score a trace via OpenEval adapter")
    parser_eval.add_argument("trace_file", help="Path to input trace file")

    args = parser.parse_args()
    
    if args.command == "record":
        record.run(args.trace_file)
    elif args.command == "replay":
        replay.run(args.trace_file)
    elif args.command == "inspect":
        inspect.run(args.trace_file)
    elif args.command == "view":
        view.run(args.trace_file)
    elif args.command == "eval":
        eval.run(args.trace_file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
