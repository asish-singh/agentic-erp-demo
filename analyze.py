#!/usr/bin/env python3
"""
Reads every run log under runs/, reconstructs per-task outcomes, and writes
findings/results.md with per-task tables and aggregate stats, including an
error taxonomy (auth, csrf, payload rejected, model gave up, and so on).

Usage:
  python analyze.py
"""

from __future__ import annotations

import glob
import json
import os
from collections import Counter, defaultdict

RUNS_DIR = "runs"
FINDINGS_DIR = "findings"
OUTPUT_FILE = os.path.join(FINDINGS_DIR, "results.md")

DEFAULT_MODEL = "openai/gpt-4o-mini"
LEGACY_TASK_ID = "find_supplier_payment_terms"


def load_run(path: str) -> dict | None:
    task_end = None
    task_start = None
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("event") == "task_start":
                task_start = record
            if record.get("event") == "task_end":
                task_end = record
    if task_end is None:
        return None
    task_end["log_path"] = path
    task_end["instruction"] = task_start.get("instruction") if task_start else ""
    task_end["model"] = (task_start or {}).get("model") or DEFAULT_MODEL
    return task_end


def collect_runs() -> list[dict]:
    paths = sorted(glob.glob(os.path.join(RUNS_DIR, "*.jsonl")))
    runs = []
    for path in paths:
        record = load_run(path)
        if record:
            runs.append(record)
    return runs


def build_report(runs: list[dict]) -> str:
    if not runs:
        return (
            "# Experiment findings\n\n"
            "No run logs found yet. Run python run_experiment.py --all "
            "to generate results.\n"
        )

    by_task = defaultdict(list)
    for run in runs:
        by_task[run["task_id"]].append(run)

    total = len(runs)
    successes = sum(1 for r in runs if r["outcome"] == "success")
    success_rate = successes / total * 100
    avg_turns = sum(r["turns"] for r in runs) / total
    avg_api_calls = sum(r["api_calls"] for r in runs) / total

    error_taxonomy = Counter()
    for run in runs:
        for error in run.get("errors", []):
            error_taxonomy[error.get("type", "unknown_error")] += 1

    lines = ["# Experiment findings", ""]
    lines.append(
        f"Across {total} logged run(s), the agent reached success on "
        f"{successes} ({success_rate:.0f} percent), using an average of "
        f"{avg_turns:.1f} turns and {avg_api_calls:.1f} SAP API calls per run."
    )
    lines.append("")

    lines.append("## Per task results")
    lines.append("")
    lines.append("| Task | Outcome | Turns | API calls | Errors | Notes |")
    lines.append("|---|---|---|---|---|---|")
    for task_id, task_runs in sorted(by_task.items()):
        for run in task_runs:
            notes = (run.get("notes") or "").replace("\n", " ").strip()
            if len(notes) > 140:
                notes = notes[:137] + "..."
            lines.append(
                f"| {task_id} | {run['outcome']} | {run['turns']} | "
                f"{run['api_calls']} | {len(run.get('errors', []))} | {notes} |"
            )
    lines.append("")

    lines.append("## Results by model")
    lines.append("")
    by_model = defaultdict(list)
    for run in runs:
        by_model[run["model"]].append(run)

    for model in sorted(by_model):
        model_runs = by_model[model]
        m_total = len(model_runs)
        m_success = sum(1 for r in model_runs if r["outcome"] == "success")
        m_rate = m_success / m_total * 100
        m_avg_calls = sum(r["api_calls"] for r in model_runs) / m_total
        lines.append(f"### {model}")
        lines.append("")
        lines.append(
            f"{m_success} of {m_total} run(s) succeeded ({m_rate:.0f} percent), "
            f"averaging {m_avg_calls:.1f} SAP API calls per run."
        )
        lines.append("")
        lines.append("| Task | Outcome | Turns | API calls |")
        lines.append("|---|---|---|---|")
        for run in sorted(model_runs, key=lambda r: r["task_id"]):
            lines.append(
                f"| {run['task_id']} | {run['outcome']} | {run['turns']} | "
                f"{run['api_calls']} |"
            )
        lines.append("")

    lines.append("## Cross model comparison")
    lines.append("")
    models_sorted = sorted(by_model)
    task_ids = sorted(
        {r["task_id"] for r in runs if r["task_id"] != LEGACY_TASK_ID}
    )
    header = "| Task | " + " | ".join(models_sorted) + " |"
    sep = "|---|" + "|".join(["---"] * len(models_sorted)) + "|"
    lines.append(header)
    lines.append(sep)
    for task_id in task_ids:
        row = [task_id]
        for model in models_sorted:
            match = next(
                (r for r in by_model[model] if r["task_id"] == task_id), None
            )
            if match:
                row.append(f"{match['outcome']}, {match['api_calls']} calls")
            else:
                row.append("not run")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append(
        f"Footnote, a legacy run of `{LEGACY_TASK_ID}` (failed, pre fix harness) "
        "is kept in runs/ for the record but excluded from this table since that "
        "task no longer exists in the current task set."
    )
    lines.append("")

    lines.append("## Aggregate stats")
    lines.append("")
    lines.append(f"- Total runs logged, {total}")
    lines.append(f"- Success rate, {success_rate:.0f} percent")
    lines.append(f"- Average turns per run, {avg_turns:.1f}")
    lines.append(f"- Average SAP API calls per run, {avg_api_calls:.1f}")
    lines.append("")

    lines.append("## Error taxonomy")
    lines.append("")
    if error_taxonomy:
        lines.append("| Error type | Count |")
        lines.append("|---|---|")
        for error_type, count in error_taxonomy.most_common():
            lines.append(f"| {error_type} | {count} |")
    else:
        lines.append("No errors logged across these runs.")
    lines.append("")

    outcome_counts = Counter(r["outcome"] for r in runs)
    lines.append("## Outcome breakdown")
    lines.append("")
    lines.append("| Outcome | Count |")
    lines.append("|---|---|")
    for outcome, count in outcome_counts.most_common():
        lines.append(f"| {outcome} | {count} |")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    runs = collect_runs()
    report = build_report(runs)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"Wrote {OUTPUT_FILE} from {len(runs)} run log(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
