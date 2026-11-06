# Decision Statuses & Resolution Precedence

Every invoice processed by InvoiceIQ concludes with one of five deterministic decision statuses computed by the `financial-validation-engine`.

## 1. Decision Status Definitions

| Status | Code | Meaning | System Action |
| :--- | :--- | :--- | :--- |
| **APPROVED** | `APPROVED` | Exact match across PO, GRN (if 3-way), quantities, unit prices, tax, and arithmetic. | Commits PO balance; ready for ERP payment export. |
| **APPROVED WITH TOLERANCE** | `APPROVED_WITH_TOLERANCE` | All hard constraints met; minor price variance exists but falls within the pre-authorized tolerance (≤ 2.0%). | Commits PO balance; logs variance alert in audit record; ready for payment. |
| **PENDING CONFIRMATION** | `PENDING_CONFIRMATION` | AI extraction confidence score is low, or human review is explicitly requested on optional metadata. | Does NOT commit PO balance; routes to AP Officer review inbox with diff view. |
| **HOLD FOR REVIEW** | `HOLD_FOR_REVIEW` | Missing external dependency (e.g., GRN not yet entered by warehouse, or pending PO amendment). | Does NOT commit PO balance; alerts warehouse/procurement; allows scheduled re-run. |
| **BLOCKED** | `BLOCKED` | Irreconcilable policy violation: unauthorized vendor, duplicate invoice, price overbilling > tolerance, or exhausted PO cap. | Does NOT commit PO balance; flags invoice as rejected with clear explanatory reasons. |

## 2. Deterministic Validation Sequence & Precedence

To eliminate conflicting statuses, the engine runs validation checks in a strict waterfall order. The first critical failure halts progression and determines the status.

```
[Start Validation]
       │
       ▼
1. Duplicate Check ────────────────────────► (Match Found) ────────► BLOCKED (Duplicate Invoice)
       │ (Pass)
       ▼
2. Vendor Master Registry Check ───────────► (Not Found) ──────────► BLOCKED (Unknown Vendor)
       │ (Pass)
       ▼
3. PO Existence & Validity Check ──────────► (Invalid/Expired) ────► BLOCKED (Invalid PO)
       │ (Pass)
       ▼
4. Line Item / SKU Alignment Check ────────► (Unknown SKU) ────────► BLOCKED (Item not on PO)
       │ (Pass)
       ▼
5. Arithmetic Integrity (Lines vs Header) ──► (Discrepancy) ───────► BLOCKED (Math Inconsistency)
       │ (Pass)
       ▼
6. PO Capacity Check (Cumulative Cap) ─────► (Quantity Exceeded) ──► BLOCKED (Exceeds PO Cap)
       │ (Pass)
       ▼
7. Matching Mode Routing (2-Way vs 3-Way)
       ├─ If 3-Way: Check GRN Existence ───► (GRN Missing) ────────► HOLD_FOR_REVIEW (Awaiting GRN)
       │            Check GRN Quantity ────► (GRN Qty < Invoice) ──► HOLD_FOR_REVIEW (Partial Delivery)
       ▼ (Pass)
8. Price Tolerance Evaluation
       ├─ Variance > 2.0% ────────────────────────────────────────► BLOCKED (Overbilling Variance)
       ├─ 0.0% < Variance <= 2.0% ───────────────────────────────► APPROVED_WITH_TOLERANCE
       └─ Variance == 0.0% ───────────────────────────────────────► APPROVED
```

## 3. Human Revalidation Rules
1. A human operator may modify line items (e.g., fixing an OCR misinterpreted digit).
2. Saving changes invokes `revalidate_invoice(invoice_id, updated_data)`.
3. The engine re-executes the exact validation sequence from Step 1 through Step 8.
4. If all checks now pass, the invoice updates to `APPROVED` and atomically claims the PO allocation.
