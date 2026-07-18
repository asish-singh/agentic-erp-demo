# Experiment findings

Across 16 logged run(s), the agent reached success on 11 (69 percent), using an average of 6.2 turns and 3.6 SAP API calls per run.

## Per task results

| Task | Outcome | Turns | API calls | Errors | Notes |
|---|---|---|---|---|---|
| create_purchase_order | gave_up | 4 | 2 | 1 | Attempted to create a new purchase order for supplier 17300001, company code 1710, but the operation is not supported in this environment... |
| create_purchase_order | failed | 5 | 3 | 2 | Creating a purchase order via POST is not supported in this sandbox. The API restricts write operations to production systems only; only ... |
| create_purchase_order | gave_up | 6 | 5 | 3 | Failed to create a new purchase order due to the 'Try-it-out' feature not being supported for POST operations in the sandbox environment. |
| find_product_base_unit | success | 6 | 4 | 1 | Found product base units and types: 1. Base Unit: H, Product Type: SERV 2. Base Unit: KG, Product Type: MAT 3. Base Unit: KG, Product Typ... |
| find_product_base_unit | success | 2 | 1 | 0 | Product 21 is of type SERV and has base unit H |
| find_product_base_unit | success | 3 | 1 | 0 | Product found: 21. Base unit of measure: H. Product type: SERV. |
| find_supplier_capital_fasteners | success | 13 | 11 | 3 | Found supplier 'Capital Fasteners Inc' with supplier number '1000033' and supplier account group 'SUPL'. |
| find_supplier_capital_fasteners | success | 3 | 1 | 0 | Capital Fasteners Inc found. Supplier number: 1000033. Supplier account group: SUPL. |
| find_supplier_capital_fasteners | gave_up | 5 | 3 | 4 | Reached max turns (15) without calling finish. |
| find_supplier_payment_terms | failed | 13 | 12 | 7 | Model call failed: Error code: 413 - {'error': {'code': 'tokens_limit_reached', 'message': 'Request body too large for gpt-4o-mini model.... |
| list_purchase_orders_for_supplier | success | 3 | 1 | 0 | Retrieved 5 purchase orders for supplier 17300001 in company code 1710. Document currencies are all USD. |
| list_purchase_orders_for_supplier | success | 3 | 1 | 0 | Listed 5 purchase orders for supplier 17300001 in company code 1710. Purchase Orders: 4500000001, 4500000002, 4500000003, 4500000004, 450... |
| list_purchase_orders_for_supplier | success | 13 | 3 | 2 | Retrieved 5 purchase orders for supplier 17300001 in company code 1710 using API_PURCHASEORDER_PROCESS_SRV. Their document currencies are... |
| summarize_supplier_invoices | success | 6 | 4 | 2 | Fetched 5 supplier invoices: 1) Invoice 5100000001 - Amount: 1511.63, Status: 5; 2) Invoice 5100000002 - Amount: 1511.63, Status: 5; 3) I... |
| summarize_supplier_invoices | success | 7 | 5 | 3 | Found 10 supplier invoices. The available fields are SupplierInvoice and DocumentDate. Status and amount fields are not available. Invoic... |
| summarize_supplier_invoices | success | 7 | 1 | 1 | Fetched 10 supplier invoices with status and gross amount. All invoices have a status of '1000' and gross amounts ranging from 100.00 to ... |

## Results by model

### meta/llama-4-maverick-17b-128e-instruct-fp8

3 of 5 run(s) succeeded (60 percent), averaging 2.6 SAP API calls per run.

| Task | Outcome | Turns | API calls |
|---|---|---|---|
| create_purchase_order | gave_up | 6 | 5 |
| find_product_base_unit | success | 2 | 1 |
| find_supplier_capital_fasteners | gave_up | 5 | 3 |
| list_purchase_orders_for_supplier | success | 13 | 3 |
| summarize_supplier_invoices | success | 7 | 1 |

### openai/gpt-4.1

4 of 5 run(s) succeeded (80 percent), averaging 2.2 SAP API calls per run.

| Task | Outcome | Turns | API calls |
|---|---|---|---|
| create_purchase_order | failed | 5 | 3 |
| find_product_base_unit | success | 3 | 1 |
| find_supplier_capital_fasteners | success | 3 | 1 |
| list_purchase_orders_for_supplier | success | 3 | 1 |
| summarize_supplier_invoices | success | 7 | 5 |

### openai/gpt-4o-mini

4 of 6 run(s) succeeded (67 percent), averaging 5.7 SAP API calls per run.

| Task | Outcome | Turns | API calls |
|---|---|---|---|
| create_purchase_order | gave_up | 4 | 2 |
| find_product_base_unit | success | 6 | 4 |
| find_supplier_capital_fasteners | success | 13 | 11 |
| find_supplier_payment_terms | failed | 13 | 12 |
| list_purchase_orders_for_supplier | success | 3 | 1 |
| summarize_supplier_invoices | success | 6 | 4 |

## Cross model comparison

| Task | meta/llama-4-maverick-17b-128e-instruct-fp8 | openai/gpt-4.1 | openai/gpt-4o-mini |
|---|---|---|---|
| create_purchase_order | gave_up, 5 calls | failed, 3 calls | gave_up, 2 calls |
| find_product_base_unit | success, 1 calls | success, 1 calls | success, 4 calls |
| find_supplier_capital_fasteners | gave_up, 3 calls | success, 1 calls | success, 11 calls |
| list_purchase_orders_for_supplier | success, 3 calls | success, 1 calls | success, 1 calls |
| summarize_supplier_invoices | success, 1 calls | success, 5 calls | success, 4 calls |

Footnote, a legacy run of `find_supplier_payment_terms` (failed, pre fix harness) is kept in runs/ for the record but excluded from this table since that task no longer exists in the current task set.

## Aggregate stats

- Total runs logged, 16
- Success rate, 69 percent
- Average turns per run, 6.2
- Average SAP API calls per run, 3.6

## Error taxonomy

| Error type | Count |
|---|---|
| not_found | 14 |
| payload_rejected | 5 |
| auth | 4 |
| unknown_error | 3 |
| model_error | 1 |
| bad_arguments | 1 |
| turn_cap_exceeded | 1 |

## Outcome breakdown

| Outcome | Count |
|---|---|
| success | 11 |
| gave_up | 3 |
| failed | 2 |
