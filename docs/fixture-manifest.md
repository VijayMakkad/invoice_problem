# Synthetic Test Fixtures Manifest

This manifest defines the standardized test data fixtures for evaluating InvoiceIQ against all business scenarios.

## 1. Master Purchase Orders (`tests/fixtures/excel/Purchase_Orders.xlsx`)

| PO Number | Vendor Name | Vendor Tax ID | Type | Line # | SKU | Description | Qty | Unit Price | Line Total |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PO-2024-001` | CloudScale IT Solutions | US-EIN-987654 | TWO_WAY | 1 | `SVC-DEV-01` | Cloud DevOps Consulting (Hours) | 100.0 | \$150.00 | \$15,000.00 |
| `PO-2024-002` | Nordic Office Logistics | NO-VAT-112233 | THREE_WAY | 1 | `HW-DESK-01` | Ergonomic Standing Desk | 10.0 | \$450.00 | \$4,500.00 |
| `PO-2024-002` | Nordic Office Logistics | NO-VAT-112233 | THREE_WAY | 2 | `HW-CHAIR-02` | Ergonomic Mesh Chair | 20.0 | \$250.00 | \$5,000.00 |
| `PO-2024-003` | Apex Industrial Supply | US-EIN-445566 | THREE_WAY | 1 | `IND-BOLT-M8` | Industrial Grade M8 Fasteners | 1000.0 | \$2.00 | \$2,000.00 |
| `PO-2024-004` | Precision Tooling Corp | US-EIN-778899 | TWO_WAY | 1 | `TOOL-DRILL-X` | High-Speed CNC Drill Bits | 50.0 | \$80.00 | \$4,000.00 |

## 2. Goods Received Notes (`tests/fixtures/excel/Goods_Receipts.xlsx`)

| GRN Number | PO Number | Vendor Name | Line # | SKU | Qty Received | Condition | Date |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GRN-2024-002` | `PO-2024-002` | Nordic Office Logistics | 1 | `HW-DESK-01` | 10.0 | GOOD | 2024-10-15 |
| `GRN-2024-002` | `PO-2024-002` | Nordic Office Logistics | 2 | `HW-CHAIR-02` | 20.0 | GOOD | 2024-10-15 |
| `GRN-2024-003` | `PO-2024-003` | Apex Industrial Supply | 1 | `IND-BOLT-M8` | 1000.0 | GOOD | 2024-10-18 |

## 3. Invoice Test PDFs & Expected Golden Outcomes

| Fixture File | Scenario | Key Attribute | Expected Status | Root Cause / Note |
| :--- | :--- | :--- | :--- | :--- |
| `INV-H1-TwoWay.pdf` | Happy 2-Way | 100 hrs consulting @ \$150 | `APPROVED` | Exact match against PO-2024-001 |
| `INV-H2-ThreeWay.pdf` | Happy 3-Way | Desks & Chairs matching GRN | `APPROVED` | Exact match against PO-2024-002 & GRN-2024-002 |
| `INV-H3-Tolerance.pdf` | Tolerance Pass | \$2.03 per bolt vs \$2.00 PO (+1.5%) | `APPROVED_WITH_TOLERANCE` | Within 2% tolerance threshold |
| `INV-E1-Overbilling.pdf` | Overbilling | \$100/drill vs \$80 PO (+25%) | `BLOCKED` | Unit price variance exceeds tolerance |
| `INV-E2-CapExceeded.pdf` | Cap Exceeded | Billing 70 drill bits vs 50 cap | `BLOCKED` | Billed quantity exceeds unallocated PO balance |
| `INV-E3-MissingGRN.pdf` | Missing GRN | Physical goods invoice with no GRN | `HOLD_FOR_REVIEW` | Required 3-way match cannot proceed without GRN |
| `INV-E4-Duplicate.pdf` | Duplicate | Resubmission of INV-H1-TwoWay | `BLOCKED` | Unique constraint (vendor_id, invoice_number) |
| `INV-E5-UnknownVendor.pdf`| Unknown Vendor | "Ghost Vendor LLC" not in master DB | `BLOCKED` | Vendor not authorized in vendor registry |
