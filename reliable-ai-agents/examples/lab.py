"""Deterministic lab drivers; no model credentials are used."""

import argparse
import json

from settings import FIXTURES, STATE
from tickets import draft_note
from tools import BudgetExceeded, RunControl, functions


def fixed_workflow(order_id: str) -> dict:
    control = RunControl()
    health, read_order, read_logs, read_runbooks, *_ = functions(control)
    return {
        "health": json.loads(health()),
        "order": json.loads(read_order(order_id)),
        "logs": json.loads(read_logs(order_id)),
        "runbooks": json.loads(read_runbooks()),
        "status": "evidence-collected",
        "warning": "Evidence collection is not a diagnosis or proof of task completion.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health")
    p = sub.add_parser("workflow")
    p.add_argument("order_id")
    sub.add_parser("loop")
    p = sub.add_parser("draft")
    p.add_argument("ticket_id", type=int)
    p.add_argument("body")
    p = sub.add_parser("notebook")
    p.add_argument("order_id")
    sub.add_parser("cases")
    args = parser.parse_args()
    if args.command == "health":
        print(functions(RunControl())[0]())
    elif args.command == "workflow":
        print(json.dumps(fixed_workflow(args.order_id), indent=2))
    elif args.command == "loop":
        # Finite naive comparison, never an actual unbounded loop.
        naive = functions(RunControl(max_calls=5, max_repeats=5))[0]
        print("Naive comparison: three identical requests, without interpreting progress.")
        for _ in range(3):
            print(naive())
        bounded = functions(RunControl(max_calls=4, max_repeats=2))[0]
        try:
            for _ in range(4):
                print(bounded())
        except BudgetExceeded as exc:
            print(json.dumps({"status": "blocked", "reason": str(exc)}))
    elif args.command == "draft":
        print(json.dumps(draft_note(args.ticket_id, args.body), indent=2))
    elif args.command == "notebook":
        evidence = fixed_workflow(args.order_id)
        STATE.mkdir(exist_ok=True)
        target = STATE / "evidence-notebook.json"
        target.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(f"Saved source-labelled observations to {target}; review freshness before reuse.")
    elif args.command == "cases":
        print((FIXTURES / "cases.json").read_text())


if __name__ == "__main__":
    main()
