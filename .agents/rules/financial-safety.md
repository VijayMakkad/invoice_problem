# Rule: Financial Safety & Decision Invariants

## 1. Zero Autonomous Approval by AI
- Large Language Models (LLMs) and Document AI vision models must **NEVER** determine the approval status of an invoice.
- LLMs are strictly limited to perception: parsing text, classifying document types, and extracting candidate structured key-value pairs into a Pydantic schema.
- All final decisions (`APPROVED`, `APPROVED_WITH_TOLERANCE`, `PENDING_CONFIRMATION`, `HOLD_FOR_REVIEW`, `BLOCKED`) must be derived by the deterministic Python validation engine.

## 2. Monetary Arithmetic Invariants
- All monetary amounts, unit costs, quantities, line totals, tax calculations, and cumulative balances must be represented using Python's `decimal.Decimal`.
- Floating point data types (`float`, `np.float64`) are strictly prohibited in financial calculations.
- Rounding modes must be explicitly specified (standard: `ROUND_HALF_UP`) and documented.

## 3. Hard Blocker Precedence Over Tolerances
- Price tolerances (e.g., standard ±2% or configured vendor thresholds) only apply when all prerequisite hard constraints are satisfied:
  - Vendor identity is verified.
  - Purchase Order exists, is active, and matches vendor.
  - SKU/item codes exist on the referenced PO.
  - Line item arithmetic matches headers.
- Tolerances can **NEVER** override a hard blocker (such as an unauthorized vendor, duplicate invoice number, missing line item on PO, or exceeded cumulative PO budget cap).

## 4. PO Allocation Safety & Idempotency
- Invoices marked `HOLD_FOR_REVIEW` or `BLOCKED` must **NEVER** consume PO balances or reserve remaining quantities.
- An invoice only consumes PO line allocations upon reaching an authorized `APPROVED` or `APPROVED_WITH_TOLERANCE` state.
- Invoices in `PENDING_CONFIRMATION` do not lock or consume PO balances until confirmed by an authorized human operator.
- PO allocations must be committed within an atomic database transaction alongside the final invoice status change to prevent race conditions and double-counting.

## 5. Three-Way Matching Invariance
- If a Purchase Order line requires three-way matching (goods receipt tracking enabled), the engine must **NEVER** silently downgrade to two-way matching because a GRN is missing.
- A missing or unverified Goods Received Note must result in `HOLD_FOR_REVIEW` (or `BLOCKED` if delivery receipt is mandatory).

## 6. Complete Revalidation on Human Confirmation
- When an AP officer overrides an extraction error, corrects a tax rate, or confirms a minor variance, the system must not simply flip a flag to `APPROVED`.
- The system must re-run the entire validation engine over the modified invoice record against current PO and GRN balances.

## 7. Document Immutability
- The original raw invoice file (PDF/image) and its raw extraction output must remain immutable.
- User corrections are stored as distinct audit delta entities, recording the original value, new value, timestamp, and user identifier.
