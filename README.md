# agentic-erp-demo

Can an AI agent actually run ERP business processes? An experiment against SAP's public sandbox APIs, testing whether an AI agent can complete real processes (purchase orders, invoices, employee lookups) end to end, and a study of where it succeeds and where enterprise API design fights it.

## What this is

A small Python project that gives an AI agent (running on GitHub's free model tier) a set of realistic SAP business tasks and lets it try to complete them by calling SAP's public sandbox OData APIs. Every model response and every API call is logged in full, so the published findings are traceable back to real runs, not summarized from memory.

The five tasks live in `tasks.yaml`, for example finding a supplier's payment terms, listing purchase orders over a given amount, and creating a new purchase order (the one task that writes data instead of just reading it).

## How to run it locally

You need Python 3.11 or later.

1. Create a virtual environment and install dependencies.

   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Set two environment variables.

   `GITHUB_TOKEN`, a GitHub personal access token with the `models:read` permission, used to call GitHub Models for free.

   `SAP_API_KEY`, a free API key from an SAP Business Accelerator Hub account at api.sap.com, used to call the SAP sandbox.

3. Run every task and see a plain summary table.

   ```
   python run_experiment.py --all
   ```

   Or run one task by id.

   ```
   python run_experiment.py --task find_supplier_payment_terms
   ```

4. Turn the logged runs into a findings report.

   ```
   python analyze.py
   ```

   This writes `findings/results.md` with a table of outcomes per task, aggregate success rate and turn counts, and a breakdown of error types (authentication, CSRF token handling, rejected payloads, and cases where the model gave up).

### Trying it without any API keys

Add `--dry-run` to any command. This swaps in canned SAP like responses and a scripted stand in for the model, so you can see the whole loop and the logging format working without signing up for anything.

```
python run_experiment.py --all --dry-run
python analyze.py
```

## Running it in GitHub Actions

The repo includes a manual workflow at `.github/workflows/experiment.yml`. Trigger it from the Actions tab in GitHub. It runs all five tasks using the repository's `GITHUB_TOKEN` (needs the `models:read` permission, already set in the workflow) and a `SAP_API_KEY` repository secret you add yourself, then uploads the raw run logs as a downloadable artifact and commits the updated `findings/results.md` back to the repo.

## Project layout

`runner/` is the agent loop package, the SAP client, the tool definitions the model can call, and the JSONL run logger.

`tasks.yaml` lists the five business tasks the agent attempts.

`run_experiment.py` is the command line entry point that runs tasks and prints a summary.

`analyze.py` reads every run log under `runs/` and writes `findings/results.md`.

`runs/` holds one JSONL log file per run, one JSON object per line, kept as the raw evidence behind the published findings.

`findings/results.md` is the generated report, safe to read on its own without running anything.
