"""CLI entry points: check, run, advise.

Usage:
    python -m deepseek_mcp check           # validate key, make 1 flash call
    python -m deepseek_mcp run <prompt>     # one-shot flash call
    python -m deepseek_mcp advise <prompt>  # one-shot advisor call
                         [--effort medium|high|max] [--show-reasoning]
"""

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deepseek-mcp",
        description="DeepSeek MCP CLI — smoke-test or one-shot calls.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check", help="Validate API key and make a test call")
    check_parser.add_argument(
        "--model", default="deepseek-v4-flash",
        help="Model to test with (default: deepseek-v4-flash)",
    )

    run_parser = sub.add_parser("run", help="One-shot flash call")
    run_parser.add_argument("prompt", help="Task prompt")

    advise_parser = sub.add_parser("advise", help="One-shot advisor call (pro+thinking)")
    advise_parser.add_argument("prompt", help="Question or problem")
    advise_parser.add_argument(
        "--effort", choices=["medium", "high", "max"], default="max",
    )

    args = parser.parse_args()

    if args.command == "check":
        _cmd_check(args)
    elif args.command == "run":
        _cmd_run(args)
    elif args.command == "advise":
        _cmd_advise(args)


def _cmd_check(args: argparse.Namespace) -> None:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        print("FAIL: DEEPSEEK_API_KEY not set.")
        print("Get a key at https://platform.deepseek.com/api_keys")
        sys.exit(2)
    if len(key) < 8:
        print("FAIL: DEEPSEEK_API_KEY looks too short.")
        sys.exit(2)
    print(f"Key found ({len(key)} chars). Making test call with {args.model}...", flush=True)

    os.environ.setdefault("DEEPSEEK_API_KEY", key)

    from deepseek_mcp.server import call_deepseek
    result = call_deepseek({"prompt": "Return exactly: ok"})
    print(result)
    print("\nPASS: deepseek-mcp is working.")


def _cmd_run(args: argparse.Namespace) -> None:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        print("FAIL: DEEPSEEK_API_KEY not set.", file=sys.stderr)
        sys.exit(2)

    from deepseek_mcp.server import call_deepseek
    result = call_deepseek({"prompt": args.prompt})
    print(result)


def _cmd_advise(args: argparse.Namespace) -> None:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        print("FAIL: DEEPSEEK_API_KEY not set.", file=sys.stderr)
        sys.exit(2)

    from deepseek_mcp.server import call_advisor
    call_args = {"prompt": args.prompt, "effort": args.effort, "system": None}
    result = call_advisor(call_args)
    print(result)


if __name__ == "__main__":
    main()
