"""
Tool definitions exposed to the model, in OpenAI function-calling format,
plus the dispatcher that executes a tool call against the SAP client (real
or dry-run stub) and returns a JSON-serializable result.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

MAX_RECORDS = 10
MAX_SERIALIZED_CHARS = 2500


def _strip_for_model(value: Any) -> Any:
    """Recursively drops OData `__metadata` keys and null valued fields so
    the model-facing copy of a response is much smaller than the raw SAP
    payload. The full, untouched response is still logged separately."""
    if isinstance(value, dict):
        cleaned = {}
        for key, val in value.items():
            if key == "__metadata":
                continue
            if val is None:
                continue
            cleaned[key] = _strip_for_model(val)
        return cleaned
    if isinstance(value, list):
        return [_strip_for_model(item) for item in value]
    return value


def _trim_result_for_model(result: dict) -> dict:
    """Builds the trimmed, model-facing copy of a tool result: strips
    __metadata and nulls, caps result lists at MAX_RECORDS, and hard-caps the
    serialized size with a truncation note. Does not mutate the input, so
    the original (full) result can still be logged in full."""
    trimmed = _strip_for_model(result)

    body = trimmed.get("body") if isinstance(trimmed, dict) else None
    if isinstance(body, dict):
        d = body.get("d")
        results = d.get("results") if isinstance(d, dict) else None
        if isinstance(results, list) and len(results) > MAX_RECORDS:
            dropped = len(results) - MAX_RECORDS
            d["results"] = results[:MAX_RECORDS]
            d[f"_truncation_note"] = f"[truncated, {dropped} more records]"

    serialized = json.dumps(trimmed, default=str)
    if len(serialized) > MAX_SERIALIZED_CHARS:
        cut = serialized[: MAX_SERIALIZED_CHARS - 200]
        # Return a minimal, valid-JSON-ish dict rather than broken JSON text.
        trimmed = {
            "status_code": trimmed.get("status_code") if isinstance(trimmed, dict) else None,
            "ok": trimmed.get("ok") if isinstance(trimmed, dict) else None,
            "truncated": True,
            "note": "[truncated, response exceeded ~2500 characters, further records omitted]",
            "partial_body_preview": cut,
        }
    return trimmed

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "odata_get",
            "description": (
                "Read data from an SAP OData service. Use this to look up "
                "business partners, purchase orders, supplier invoices, or "
                "products. query_params supports OData options such as "
                "$filter, $top, $select."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "SAP OData service name, e.g. API_BUSINESS_PARTNER",
                    },
                    "entity": {
                        "type": "string",
                        "description": "Entity set name, e.g. A_BusinessPartner",
                    },
                    "query_params": {
                        "type": "object",
                        "description": "OData query options as key-value pairs, e.g. {\"$filter\": \"...\"}",
                    },
                },
                "required": ["service", "entity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "odata_post",
            "description": (
                "Create a record in an SAP OData service, such as a new "
                "purchase order. Handles the CSRF token exchange for you."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string"},
                    "entity": {"type": "string"},
                    "payload": {
                        "type": "object",
                        "description": "Body of the record to create",
                    },
                },
                "required": ["service", "entity", "payload"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_services",
            "description": "List the SAP OData services and main entities available in this sandbox.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": (
                "Call this when the task is complete or you are giving up. "
                "This ends the run."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "outcome": {
                        "type": "string",
                        "enum": ["success", "partial", "gave_up", "failed"],
                    },
                    "notes": {
                        "type": "string",
                        "description": "Plain summary of what happened and any answer found",
                    },
                },
                "required": ["outcome", "notes"],
            },
        },
    },
]


def dispatch_tool_call(sap_client, name: str, arguments: dict) -> dict[str, Any]:
    """Executes one tool call and returns a JSON-serializable dict."""
    if name == "list_available_services":
        return sap_client.list_available_services()

    if name == "odata_get":
        result = sap_client.odata_get(
            service=arguments.get("service"),
            entity=arguments.get("entity"),
            query_params=arguments.get("query_params") or {},
        )
        return asdict(result)

    if name == "odata_post":
        result = sap_client.odata_post(
            service=arguments.get("service"),
            entity=arguments.get("entity"),
            payload=arguments.get("payload") or {},
        )
        return asdict(result)

    if name == "finish":
        return {"acknowledged": True}

    return {"error": f"Unknown tool: {name}"}


def trim_tool_result_for_model(result: dict) -> dict:
    """Public entry point: returns a trimmed, model-facing copy of a tool
    result. The caller should log the untouched `result` in full and only
    feed this trimmed copy into the model conversation."""
    if not isinstance(result, dict):
        return result
    return _trim_result_for_model(result)
