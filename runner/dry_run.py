"""
Stub SAP client used by --dry-run. Returns canned, SAP-shaped OData
responses so the agent loop and logging can be tested end to end without a
real SAP_API_KEY or network access.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from runner.sap_client import SapCallResult, SERVICES

CANNED_RESPONSES = {
    ("API_BUSINESS_PARTNER", "A_BusinessPartner"): {
        "d": {
            "results": [
                {
                    "BusinessPartner": "17300001",
                    "BusinessPartnerFullName": "Acme Robotics Supply",
                    "PaymentTerms": "NT30",
                    "CustomerPaymentTerms": "30 days net",
                }
            ]
        }
    },
    ("API_PURCHASEORDER_PROCESS_SRV", "A_PurchaseOrder"): {
        "d": {
            "results": [
                {
                    "PurchaseOrder": "4500000001",
                    "Supplier": "17300001",
                    "PurchaseOrderNetAmount": "12500.00",
                    "PurchasingDocumentType": "NB",
                    "PurchaseOrderDate": "/Date(1752537600000)/",
                }
            ]
        }
    },
    ("API_SUPPLIERINVOICE_PROCESS_SRV", "A_SupplierInvoice"): {
        "d": {
            "results": [
                {
                    "SupplierInvoice": "5105600001",
                    "InvoicingParty": "17300001",
                    "SupplierInvoiceStatus": "posted",
                    "InvoiceGrossAmount": "12500.00",
                }
            ]
        }
    },
    ("API_PRODUCT_SRV", "A_Product"): {
        "d": {
            "results": [
                {
                    "Product": "TG-2100",
                    "ProductDescription": "Precision servo motor",
                    "ProductGroup": "SERVO",
                    "Supplier": "17300001",
                }
            ]
        }
    },
}

CANNED_POST_SUCCESS = {
    "d": {
        "PurchaseOrder": "4500009999",
        "Supplier": "17300001",
        "PurchaseOrderNetAmount": "980.00",
    }
}


class DryRunSapClient:
    """Drop-in replacement for SapClient. No network calls, no API key."""

    def __init__(self, api_key: str | None = None):
        self.api_key = "dry-run-stub-key"

    def list_available_services(self) -> dict:
        return {
            "services": [
                {"service": service, "main_entity": entity}
                for service, entity in SERVICES.items()
            ]
        }

    def odata_get(self, service: str, entity: str, query_params: dict | None = None) -> SapCallResult:
        canned = CANNED_RESPONSES.get((service, entity))
        if canned is None:
            return SapCallResult(
                status_code=404,
                body={"error": {"message": f"Unknown service/entity in dry-run: {service}/{entity}"}},
                ok=False,
            )
        return SapCallResult(status_code=200, body=canned, ok=True)

    def odata_post(self, service: str, entity: str, payload: dict) -> SapCallResult:
        if not payload or not isinstance(payload, dict):
            return SapCallResult(
                status_code=400,
                body={"error": {"message": "Payload rejected: empty or malformed body"}},
                ok=False,
            )
        return SapCallResult(status_code=201, body=CANNED_POST_SUCCESS, ok=True)


def _plan_for_instruction(instruction: str) -> list[dict]:
    """A small scripted plan of tool calls per task, keyed on wording in
    tasks.yaml. Good enough to exercise the full agent loop end to end
    without a real model."""
    text = instruction.lower()

    if "payment terms" in text:
        return [
            {"name": "odata_get", "arguments": {"service": "API_BUSINESS_PARTNER", "entity": "A_BusinessPartner", "query_params": {"$filter": "BusinessPartnerFullName eq 'Acme Robotics Supply'"}}},
            {"name": "finish", "arguments": {"outcome": "success", "notes": "Acme Robotics Supply has payment terms NT30 (30 days net)."}},
        ]
    if "purchase orders with a net order value" in text:
        return [
            {"name": "odata_get", "arguments": {"service": "API_PURCHASEORDER_PROCESS_SRV", "entity": "A_PurchaseOrder", "query_params": {"$filter": "PurchaseOrderNetAmount gt 10000"}}},
            {"name": "finish", "arguments": {"outcome": "success", "notes": "Purchase order 4500000001 has a net amount of 12500.00, above the threshold."}},
        ]
    if "create a new purchase order" in text:
        return [
            {"name": "odata_get", "arguments": {"service": "API_BUSINESS_PARTNER", "entity": "A_BusinessPartner", "query_params": {"$filter": "BusinessPartnerFullName eq 'Acme Robotics Supply'"}}},
            {"name": "odata_post", "arguments": {"service": "API_PURCHASEORDER_PROCESS_SRV", "entity": "A_PurchaseOrder", "payload": {"Supplier": "17300001", "Product": "TG-2100", "Quantity": 10}}},
            {"name": "finish", "arguments": {"outcome": "success", "notes": "Created purchase order 4500009999 for supplier 17300001."}},
        ]
    if "supplier invoice" in text:
        return [
            {"name": "odata_get", "arguments": {"service": "API_SUPPLIERINVOICE_PROCESS_SRV", "entity": "A_SupplierInvoice", "query_params": {"$filter": "SupplierInvoice eq '5105600001'"}}},
            {"name": "finish", "arguments": {"outcome": "success", "notes": "Invoice 5105600001 is posted, gross amount 12500.00."}},
        ]
    if "look up product" in text or ("product" in text and "supplier" in text):
        return [
            {"name": "odata_get", "arguments": {"service": "API_PRODUCT_SRV", "entity": "A_Product", "query_params": {"$filter": "Product eq 'TG-2100'"}}},
            {"name": "odata_get", "arguments": {"service": "API_BUSINESS_PARTNER", "entity": "A_BusinessPartner", "query_params": {"$filter": "BusinessPartner eq '17300001'"}}},
            {"name": "finish", "arguments": {"outcome": "success", "notes": "Product TG-2100 (precision servo motor) is supplied by Acme Robotics Supply."}},
        ]
    return [{"name": "finish", "arguments": {"outcome": "gave_up", "notes": "Dry-run stub has no scripted plan for this instruction."}}]


class DryRunModelClient:
    """Stands in for the OpenAI client during --dry-run. Mimics the small
    slice of the chat.completions.create response shape the agent loop
    reads: choices[0].message.{content,tool_calls}, response.usage."""

    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, model, messages, tools):  # noqa: ARG002 - match real signature
        instruction = messages[1]["content"] if len(messages) > 1 else ""
        plan = _plan_for_instruction(instruction)
        # Number of prior assistant turns tells us how far through the plan we are.
        turn_index = sum(1 for m in messages if m.get("role") == "assistant")
        step = plan[min(turn_index, len(plan) - 1)]

        tool_call = SimpleNamespace(
            id=f"dryrun-call-{turn_index}",
            function=SimpleNamespace(name=step["name"], arguments=json.dumps(step["arguments"])),
        )
        message = SimpleNamespace(content=None, tool_calls=[tool_call])
        choice = SimpleNamespace(message=message)
        usage = SimpleNamespace(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        return SimpleNamespace(choices=[choice], usage=usage)
