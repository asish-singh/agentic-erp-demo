"""
Tool definitions exposed to the model, in OpenAI function-calling format,
plus the dispatcher that executes a tool call against the SAP client (real
or dry-run stub) and returns a JSON-serializable result.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

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
