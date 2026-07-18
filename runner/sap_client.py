"""
Thin client for the SAP Business Accelerator Hub sandbox APIs.

Handles the OData basics the agent needs: GET with query options, and POST
with the X-CSRF-Token fetch dance SAP's OData services require. Includes
retry with backoff and a small delay between calls to be polite to the
shared sandbox.

A --dry-run mode (see runner/dry_run.py) swaps this client for a stub that
returns canned SAP-like responses, so the whole loop can be tested without
a real SAP_API_KEY.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests

SAP_BASE_URL = "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap"

SERVICES = {
    "API_BUSINESS_PARTNER": "A_Supplier",
    "API_PURCHASEORDER_PROCESS_SRV": "A_PurchaseOrder",
    "API_SUPPLIERINVOICE_PROCESS_SRV": "A_SupplierInvoice",
    "API_PRODUCT_SRV": "A_Product",
}

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
POLITE_DELAY_SECONDS = 1


class SapApiError(Exception):
    """Raised when the SAP sandbox returns an error we cannot recover from."""


@dataclass
class SapCallResult:
    status_code: int
    body: Any
    ok: bool


class SapClient:
    """Talks to the real SAP Business Accelerator Hub sandbox."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("SAP_API_KEY")
        if not self.api_key:
            raise SapApiError(
                "SAP_API_KEY is not set. Export it or use --dry-run to test "
                "without a real key."
            )
        self.session = requests.Session()

    def list_available_services(self) -> dict:
        return {
            "services": [
                {"service": service, "main_entity": entity}
                for service, entity in SERVICES.items()
            ]
        }

    def _headers(self) -> dict:
        return {"APIKey": self.api_key, "Accept": "application/json"}

    def _url(self, service: str, entity: str) -> str:
        return f"{SAP_BASE_URL}/{service}/{entity}"

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)
                if response.status_code >= 500 and attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                    continue
                return response
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
        raise SapApiError(f"Request failed after {MAX_RETRIES} attempts: {last_exc}")

    def odata_get(self, service: str, entity: str, query_params: dict | None = None) -> SapCallResult:
        url = self._url(service, entity)
        params = dict(query_params or {})
        params.setdefault("$format", "json")
        response = self._request_with_retry("GET", url, headers=self._headers(), params=params)
        time.sleep(POLITE_DELAY_SECONDS)
        return self._to_result(response)

    def _fetch_csrf_token(self, service: str, entity: str) -> tuple[str, Any]:
        url = self._url(service, entity)
        headers = self._headers()
        headers["X-CSRF-Token"] = "Fetch"
        response = self._request_with_retry("GET", url, headers=headers)
        token = response.headers.get("X-CSRF-Token", "")
        return token, response.cookies

    def odata_post(self, service: str, entity: str, payload: dict) -> SapCallResult:
        token, cookies = self._fetch_csrf_token(service, entity)
        url = self._url(service, entity)
        headers = self._headers()
        headers["X-CSRF-Token"] = token
        headers["Content-Type"] = "application/json"
        response = self._request_with_retry(
            "POST", url, headers=headers, cookies=cookies, json=payload
        )
        time.sleep(POLITE_DELAY_SECONDS)
        return self._to_result(response)

    @staticmethod
    def _to_result(response: requests.Response) -> SapCallResult:
        try:
            body = response.json()
        except ValueError:
            body = {"raw_text": response.text[:2000]}
        return SapCallResult(status_code=response.status_code, body=body, ok=response.ok)
