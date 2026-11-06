# Acceptance Test Matrix — Zamp ASA PS-1

This matrix defines the required automated test suites and pass criteria for InvoiceIQ.

## 1. Test Suite Coverage

| Suite | File | Focus | Expected Status |
| :--- | :--- | :--- | :--- |
| **H1** | `tests/scenarios/test_happy_path_2way.py` | Services invoice matching PO #PO-2024-001 with exact lines. | `APPROVED` |
| **H2** | `tests/scenarios/test_happy_path_3way.py` | Physical goods invoice matching PO #PO-2024-002 & GRN #GRN-2024-002. | `APPROVED` |
| **H3** | `tests/scenarios/test_tolerance_path.py` | Hardware supplies invoice with +1.5% price variance (within 2% limit). | `APPROVED_WITH_TOLERANCE` |
| **E1** | `tests/scenarios/test_exception_overbilling.py` | Invoice unit price billed at \$125 vs PO price \$100 (+25%). | `BLOCKED` |
| **E2** | `tests/scenarios/test_exception_po_cap.py` | Invoicing 120 units against a PO line with only 50 remaining capacity. | `BLOCKED` |
| **E3** | `tests/scenarios/test_exception_missing_grn.py` | 3-way matching physical goods invoice submitted before GRN is entered. | `HOLD_FOR_REVIEW` |
| **E4** | `tests/scenarios/test_exception_duplicate.py` | Submitting the same invoice number for an existing vendor twice. | `BLOCKED` |
| **E5** | `tests/scenarios/test_exception_unknown_vendor.py` | Invoice from unregistered vendor entity not in vendor master. | `BLOCKED` |

## 2. Infrastructure & Provider Fallback Tests

| Test ID | Test File | Description | Assertions |
| :--- | :--- | :--- | :--- |
| **INF-01** | `tests/unit/test_provider_fallback.py` | Simulate Gemini API returning HTTP 429 quota exhaustion. | Provider fallback router triggers Ollama Qwen; logs audit event; extraction succeeds. |
| **INF-02** | `tests/unit/test_provider_timeout.py` | Simulate Gemini API hanging > 15s. | Timeout caught; triggers local Qwen; records fallback event. |
| **INF-03** | `tests/unit/test_decimal_precision.py` | High-precision decimal arithmetic over edge cases ($0.003$ tax rounding). | No IEEE-754 binary floating point precision leakage; exact penny matching. |
| **INF-04** | `tests/integration/test_atomic_commit.py` | Force database error during PO balance deduction. | Whole transaction rolls back; PO balance remains unchanged; invoice not approved. |
| **INF-05** | `tests/integration/test_revalidation.py` | Modify line item on `BLOCKED` invoice and trigger revalidation. | Engine re-evaluates all 8 steps; transitions to `APPROVED` if discrepancy resolved. |
