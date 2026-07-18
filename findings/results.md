# Experiment findings

Across 6 logged run(s), the agent reached success on 4 (67 percent), using an average of 7.5 turns and 5.7 SAP API calls per run.

## Per task results

| Task | Outcome | Turns | API calls | Errors | Notes |
|---|---|---|---|---|---|
| create_purchase_order | gave_up | 4 | 2 | 1 | Attempted to create a new purchase order for supplier 17300001, company code 1710, but the operation is not supported in this environment... |
| find_product_base_unit | success | 6 | 4 | 1 | Found product base units and types: 1. Base Unit: H, Product Type: SERV 2. Base Unit: KG, Product Type: MAT 3. Base Unit: KG, Product Typ... |
| find_supplier_capital_fasteners | success | 13 | 11 | 3 | Found supplier 'Capital Fasteners Inc' with supplier number '1000033' and supplier account group 'SUPL'. |
| find_supplier_payment_terms | failed | 13 | 12 | 7 | Model call failed: Error code: 413 - {'error': {'code': 'tokens_limit_reached', 'message': 'Request body too large for gpt-4o-mini model.... |
| list_purchase_orders_for_supplier | success | 3 | 1 | 0 | Retrieved 5 purchase orders for supplier 17300001 in company code 1710. Document currencies are all USD. |
| summarize_supplier_invoices | success | 6 | 4 | 2 | Fetched 5 supplier invoices: 1) Invoice 5100000001 - Amount: 1511.63, Status: 5; 2) Invoice 5100000002 - Amount: 1511.63, Status: 5; 3) I... |

## Aggregate stats

- Total runs logged, 6
- Success rate, 67 percent
- Average turns per run, 7.5
- Average SAP API calls per run, 5.7

## Error taxonomy

| Error type | Count |
|---|---|
| not_found | 7 |
| payload_rejected | 5 |
| model_error | 1 |
| unknown_error | 1 |

## Outcome breakdown

| Outcome | Count |
|---|---|
| success | 4 |
| failed | 1 |
| gave_up | 1 |
