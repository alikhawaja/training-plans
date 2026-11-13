"""Explicitly opt in to a cost-bearing model run."""

import argparse
import asyncio
import importlib
import json
import re
import sys

from settings import STATE


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", choices=["langchain", "microsoft"], required=True)
    parser.add_argument("--stage", choices=["first", "tools", "controlled", "harness", "delegate"], default="controlled")
    parser.add_argument("--run-id", default="investigation")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--allow-model-calls", action="store_true", required=True)
    parser.add_argument("prompt")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", args.run_id):
        raise ValueError("run-id must contain 1-60 letters, digits, underscores or hyphens")
    module = importlib.import_module(f"{args.track}_track")
    STATE.mkdir(exist_ok=True)
    result_path = STATE / f"{args.track}-{args.run_id}-report.json"
    # Clear the prior report so a failed run cannot appear to have succeeded.
    result_path.write_text(json.dumps({"status": "running"}))
    try:
        result = await module.run(args.prompt, args.run_id, args.stage, args.stream)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    except (TimeoutError, RuntimeError) as exc:
        result_path.write_text(json.dumps({"status": "partial", "reason": str(exc) or type(exc).__name__}))
        raise
    finally:
        if json.loads(result_path.read_text())["status"] == "running":
            result_path.write_text(json.dumps({
                "status": "failed",
                "reason": "Run did not return normally; inspect the emitted traceback.",
            }))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Cancelled. Inspect saved state; do not assume completion.", file=sys.stderr)
        raise SystemExit(130)
