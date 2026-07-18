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
    ("API_BUSINESS_PARTNER", "A_Supplier"): {
        "d": {
            "results": [
                {
                    "Supplier": "1000033",
                    "SupplierName": "Capital Fasteners Inc",
                    "SupplierAccountGroup": "ZSUP",
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
                    "CompanyCode": "1710",
                    "DocumentCurrency": "USD",
                    "PurchaseOrderDate": "/Date(1752537600000)/",
                },
                {
                    "PurchaseOrder": "4500000002",
                    "Supplier": "17300001",
                    "CompanyCode": "1710",
                    "DocumentCurrency": "USD",
                    "PurchaseOrderDate": "/Date(1752624000000)/",
                },
                {
                    "PurchaseOrder": "4500000003",
                    "Supplier": "17300001",
                    "CompanyCode": "1710",
                    "DocumentCurrency": "USD",
                    "PurchaseOrderDate": "/Date(1752710400000)/",
                },
                {
                    "PurchaseOrder": "4500000004",
                    "Supplier": "17300001",
                    "CompanyCode": "1710",
                    "DocumentCurrency": "USD",
                    "PurchaseOrderDate": "/Date(1752796800000)/",
                },
                {
                    "PurchaseOrder": "4500000005",
                    "Supplier": "17300001",
                    "CompanyCode": "1710",
                    "DocumentCurrency": "USD",
                    "PurchaseOrderDate": "/Date(1752883200000)/",
                },
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
                    "ProductType": "FERT",
                    "BaseUnit": "EA",
                }
            ]
        }
    },
}

CANNED_POST_REJECTED = {
    "error": {
        "code": "005056A509B11EE1B9A8FEA8DE87F78E",
        "message": {
            "lang": "en",
            "value": "Enter Purchasing Organization",
        },
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
        # Mirrors the real sandbox behavior found in live testing: a purchase
        # order create with only Supplier/CompanyCode is rejected because
        # required header/item fields (purchasing org, plant, item data) are
        # missing. This is the hard, honest outcome the task expects.
        if not payload or not isinstance(payload, dict):
            return SapCallResult(
                status_code=400,
                body={"error": {"message": "Payload rejected: empty or malformed body"}},
                ok=False,
            )
        return SapCallResult(status_code=400, body=CANNED_POST_REJECTED, ok=False)


def _plan_for_instruction(instruction: str) -> list[dict]:
    """A small scripted plan of tool calls per task, keyed on wording in
    tasks.yaml. Good enough to exercise the full agent loop end to end
    without a real model."""
    text = instruction.lower()

    if "capital fasteners" in text:
        return [
            {"name": "odata_get", "arguments": {"service": "API_BUSINESS_PARTNER", "entity": "A_Supplier", "query_params": {"$filter": "substringof('Capital Fasteners Inc', SupplierName)", "$top": 5, "$select": "Supplier,SupplierName,SupplierAccountGroup"}}},
            {"name": "finish", "arguments": {"outcome": "success", "notes": "Capital Fasteners Inc is supplier 1000033, account group ZSUP."}},
        ]
    if "list 5 purchase orders" in text or ("purchase orders" in text and "17300001" in text and "currenc" in text):
        return [
            {"name": "odata_get", "arguments": {"service": "API_PURCHASEORDER_PROCESS_SRV", "entity": "A_PurchaseOrder", "query_params": {"$filter": "Supplier eq '17300001' and CompanyCode eq '1710'", "$top": 5, "$select": "PurchaseOrder,Supplier,CompanyCode,DocumentCurrency"}}},
            {"name": "finish", "arguments": {"outcome": "success", "notes": "Found 5 purchase orders for supplier 17300001 in company code 1710 (4500000001 through 4500000005), all in USD."}},
        ]
    if "create a new purchase order" in text:
        return [
            {"name": "odata_get", "arguments": {"service": "API_BUSINESS_PARTNER", "entity": "A_Supplier", "query_params": {"$filter": "Supplier eq '17300001'", "$top": 1}}},
            {"name": "odata_post", "arguments": {"service": "API_PURCHASEORDER_PROCESS_SRV", "entity": "A_PurchaseOrder", "payload": {"Supplier": "17300001", "CompanyCode": "1710"}}},
            {"name": "finish", "arguments": {"outcome": "gave_up", "notes": "Create was rejected: sandbox requires Purchasing Organization and item data (plant, material or short text, quantity) that were not supplied. CSRF handshake itself succeeded; the 400 came from missing required fields, not auth."}},
        ]
    if "supplier invoice" in text:
        return [
            {"name": "odata_get", "arguments": {"service": "API_SUPPLIERINVOICE_PROCESS_SRV", "entity": "A_SupplierInvoice", "query_params": {"$top": 10, "$select": "SupplierInvoice,InvoicingParty,SupplierInvoiceStatus,InvoiceGrossAmount"}}},
            {"name": "finish", "arguments": {"outcome": "success", "notes": "Found 1 supplier invoice in the sandbox: 5105600001, posted, gross amount 12500.00."}},
        ]
    if "base unit" in text or ("product" in text and "product type" in text):
        return [
            {"name": "odata_get", "arguments": {"service": "API_PRODUCT_SRV", "entity": "A_Product", "query_params": {"$top": 5, "$select": "Product,ProductDescription,ProductType,BaseUnit"}}},
            {"name": "finish", "arguments": {"outcome": "success", "notes": "Product TG-2100 (precision servo motor) has base unit EA and product type FERT."}},
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
