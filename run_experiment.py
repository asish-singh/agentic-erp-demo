#!/usr/bin/env python3
"""
CLI entry point for the experiment. Runs one task or all tasks in
tasks.yaml, logs every step to runs/, and prints a plain summary table.

Usage:
  python run_experiment.py --all
  python run_experiment.py --task find_supplier_payment_terms
  python run_experiment.py --all --dry-run
"""

from __future__ import annotations

import argparse
import sys

import yaml

from runner.agent import AgentRun, DEFAULT_MAX_TURNS, DEFAULT_MODEL
from runner.log import RunLogger

RUNS_DIR = "runs"
TASKS_FILE = "tasks.yaml"


def load_tasks() -> list[dict]:
    with open(TASKS_FILE, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data["tasks"]


def build_sap_client(dry_run: bool):
    if dry_run:
        from runner.dry_run import DryRunSapClient

        return DryRunSapClient()
    from runner.sap_client import SapClient

    return SapClient()


def print_summary_table(results: list[dict]) -> None:
    headers = ["task", "outcome", "turns", "api_calls", "errors"]
    rows = [
        [
            r["task_id"],
            r["outcome"],
            str(r["turns"]),
            str(r["api_calls"]),
            str(len(r["errors"])),
        ]
        for r in results
    ]
    widths = [max(len(h), *(len(row[i]) for row in rows)) if rows else len(h) for i, h in enumerate(headers)]

    def fmt_row(row):
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    print(fmt_row(headers))
    print(fmt_row(["-" * w for w in widths]))
    for row in rows:
        print(fmt_row(row))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SAP agent experiment tasks.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Run every task in tasks.yaml")
    group.add_argument("--task", help="Run a single task by id")
    parser.add_argument("--dry-run", action="store_true", help="Use canned SAP responses, no API key or GitHub token needed for SAP calls")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="GitHub Models model id")
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS, help="Max agent turns per task")
    args = parser.parse_args()

    tasks = load_tasks()
    if args.task:
        tasks = [t for t in tasks if t["id"] == args.task]
        if not tasks:
            print(f"No task with id '{args.task}' found in {TASKS_FILE}", file=sys.stderr)
            return 1

    sap_client = build_sap_client(args.dry_run)

    results = []
    for task in tasks:
        logger = RunLogger(task["id"], RUNS_DIR, args.dry_run)
        print(f"Running task: {task['id']} (log: {logger.path})")
        agent = AgentRun(sap_client, logger, model=args.model, max_turns=args.max_turns, dry_run=args.dry_run)
        try:
            summary = agent.run_task(task)
        except Exception as exc:  # noqa: BLE001 - keep going for the rest of the batch
            summary = {
                "task_id": task["id"],
                "outcome": "failed",
                "notes": f"Run crashed: {exc}",
                "turns": 0,
                "api_calls": 0,
                "errors": [{"type": "crash", "detail": str(exc)}],
            }
            logger.write({"event": "crash", "detail": str(exc)})
        logger.close()
        results.append(summary)

    print()
    print_summary_table(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
