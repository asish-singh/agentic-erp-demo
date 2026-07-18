"""
The agent loop. Sends the task to a GitHub Models chat completion endpoint
(OpenAI-compatible), lets the model call SAP tools, feeds results back, and
stops on finish(), an error, or the turn cap.

Every model response and every tool call/result is written to the JSONL
run log so the whole attempt can be reconstructed later.
"""

from __future__ import annotations

import json
import os

from openai import OpenAI

from runner.tools import TOOL_SCHEMAS, dispatch_tool_call

GITHUB_MODELS_BASE_URL = "https://models.github.ai/inference"
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_MAX_TURNS = 15

SYSTEM_PROMPT = """You are an ERP operations agent. You complete SAP business
process tasks by calling the tools provided: odata_get, odata_post,
list_available_services, and finish.

Rules:
- Use list_available_services if you are unsure which service or entity to use.
- Use odata_get to look up data before attempting odata_post.
- When you have an answer or have completed the task, call finish with an
  outcome (success, partial, gave_up, or failed) and clear notes summarizing
  what you found or did.
- If you are stuck after a reasonable number of attempts, call finish with
  outcome gave_up rather than repeating the same call.
- Be concise. Do not narrate every step in prose, just call tools and finish.
"""


class AgentRun:
    def __init__(
        self,
        sap_client,
        logger,
        model: str = DEFAULT_MODEL,
        max_turns: int = DEFAULT_MAX_TURNS,
        dry_run: bool = False,
    ):
        self.sap_client = sap_client
        self.logger = logger
        self.max_turns = max_turns
        self.dry_run = dry_run
        self.model = model
        if dry_run:
            # No GitHub token needed: a scripted stub model stands in for the
            # real one so the whole loop, including logging, is testable.
            from runner.dry_run import DryRunModelClient

            self.client = DryRunModelClient()
            return
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            raise RuntimeError(
                "GITHUB_TOKEN is not set. It needs models:read permission for "
                "GitHub Models. Use --dry-run to test without it."
            )
        self.client = OpenAI(base_url=GITHUB_MODELS_BASE_URL, api_key=github_token)

    def run_task(self, task: dict) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task["instruction"]},
        ]
        self.logger.write({"event": "task_start", "task_id": task["id"], "instruction": task["instruction"]})

        turns = 0
        api_calls = 0
        errors = []
        outcome = "incomplete"
        notes = ""

        while turns < self.max_turns:
            turns += 1
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                )
            except Exception as exc:  # noqa: BLE001 - log and stop, don't crash the batch
                errors.append({"type": "model_error", "detail": str(exc)})
                self.logger.write({"event": "model_error", "turn": turns, "detail": str(exc)})
                outcome = "failed"
                notes = f"Model call failed: {exc}"
                break

            choice = response.choices[0]
            message = choice.message
            usage = getattr(response, "usage", None)
            self.logger.write(
                {
                    "event": "model_response",
                    "turn": turns,
                    "content": message.content,
                    "tool_calls": [
                        {"name": tc.function.name, "arguments": tc.function.arguments}
                        for tc in (message.tool_calls or [])
                    ],
                    "tokens": {
                        "prompt": getattr(usage, "prompt_tokens", None),
                        "completion": getattr(usage, "completion_tokens", None),
                        "total": getattr(usage, "total_tokens", None),
                    }
                    if usage
                    else None,
                }
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in (message.tool_calls or [])
                    ]
                    or None,
                }
            )

            if not message.tool_calls:
                # Model responded with plain text instead of calling finish. Nudge once.
                messages.append(
                    {
                        "role": "user",
                        "content": "Please call a tool, or call finish if you are done.",
                    }
                )
                continue

            finished = False
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError as exc:
                    arguments = {}
                    errors.append({"type": "bad_arguments", "detail": str(exc)})

                if name == "finish":
                    outcome = arguments.get("outcome", "incomplete")
                    notes = arguments.get("notes", "")
                    self.logger.write({"event": "finish", "turn": turns, "outcome": outcome, "notes": notes})
                    result = {"acknowledged": True}
                    finished = True
                else:
                    if name in ("odata_get", "odata_post"):
                        api_calls += 1
                    result = dispatch_tool_call(self.sap_client, name, arguments)
                    if isinstance(result, dict) and result.get("ok") is False:
                        errors.append(
                            {
                                "type": self._classify_error(result),
                                "detail": result,
                            }
                        )
                    self.logger.write(
                        {
                            "event": "tool_call",
                            "turn": turns,
                            "tool": name,
                            "arguments": arguments,
                            "result": result,
                        }
                    )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    }
                )

            if finished:
                break
        else:
            pass

        if outcome == "incomplete":
            outcome = "gave_up"
            notes = notes or f"Reached max turns ({self.max_turns}) without calling finish."
            errors.append({"type": "turn_cap_exceeded", "detail": notes})

        summary = {
            "task_id": task["id"],
            "outcome": outcome,
            "notes": notes,
            "turns": turns,
            "api_calls": api_calls,
            "errors": errors,
        }
        self.logger.write({"event": "task_end", **summary})
        return summary

    @staticmethod
    def _classify_error(result: dict) -> str:
        status = result.get("status_code")
        body = json.dumps(result.get("body", {})).lower()
        if status in (401, 403):
            return "auth"
        if "csrf" in body:
            return "csrf"
        if status == 400:
            return "payload_rejected"
        if status == 404:
            return "not_found"
        if status and status >= 500:
            return "server_error"
        return "unknown_error"
