# SQLite Database Schema & Audit Specifications

This document outlines the SQLite schema, table constraints, transaction contracts, and audit logging for InvoiceIQ.

## 1. Relational DDL (SQLite 3)

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- 1. Vendors Master Table
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tax_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, SUSPENDED, PENDING
    payment_terms TEXT DEFAULT 'NET30',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Purchase Orders Table
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_number TEXT PRIMARY KEY,
    vendor_id TEXT NOT NULL,
    issue_date DATE NOT NULL,
    matching_type TEXT NOT NULL DEFAULT 'THREE_WAY', -- TWO_WAY, THREE_WAY
    currency TEXT NOT NULL DEFAULT 'USD',
    total_amount NUMERIC NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, CLOSED, CANCELLED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
);

-- 3. PO Line Items Table
CREATE TABLE IF NOT EXISTS po_line_items (
    po_number TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    sku TEXT NOT NULL,
    description TEXT NOT NULL,
    quantity_ordered NUMERIC NOT NULL,
    quantity_allocated NUMERIC NOT NULL DEFAULT 0,
    unit_price NUMERIC NOT NULL,
    tolerance_percent NUMERIC NOT NULL DEFAULT 0.02,
    PRIMARY KEY (po_number, line_number),
    FOREIGN KEY (po_number) REFERENCES purchase_orders(po_number) ON DELETE CASCADE
);

-- 4. Goods Received Notes Table
CREATE TABLE IF NOT EXISTS goods_receipt_notes (
    grn_number TEXT PRIMARY KEY,
    po_number TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    received_date DATE NOT NULL,
    received_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (po_number) REFERENCES purchase_orders(po_number)
);

-- 5. GRN Line Items Table
CREATE TABLE IF NOT EXISTS grn_line_items (
    grn_number TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    po_line_number INTEGER NOT NULL,
    sku TEXT NOT NULL,
    quantity_received NUMERIC NOT NULL,
    quantity_invoiced NUMERIC NOT NULL DEFAULT 0,
    receipt_condition TEXT NOT NULL DEFAULT 'GOOD',
    PRIMARY KEY (grn_number, line_number),
    FOREIGN KEY (grn_number) REFERENCES goods_receipt_notes(grn_number) ON DELETE CASCADE
);

-- 6. Invoices Table
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    invoice_number TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,
    po_number TEXT,
    invoice_date DATE NOT NULL,
    subtotal NUMERIC NOT NULL,
    tax_total NUMERIC NOT NULL,
    grand_total NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL, -- APPROVED, APPROVED_WITH_TOLERANCE, PENDING_CONFIRMATION, HOLD_FOR_REVIEW, BLOCKED
    decision_reason TEXT,
    raw_document_hash TEXT NOT NULL,
    extraction_provider TEXT NOT NULL, -- 'gemini' or 'qwen'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vendor_id, invoice_number),
    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id),
    FOREIGN KEY (po_number) REFERENCES purchase_orders(po_number)
);

-- 7. Invoice Line Items Table
CREATE TABLE IF NOT EXISTS invoice_line_items (
    invoice_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    sku TEXT,
    description TEXT NOT NULL,
    quantity NUMERIC NOT NULL,
    unit_price NUMERIC NOT NULL,
    line_total NUMERIC NOT NULL,
    tax_amount NUMERIC DEFAULT 0,
    PRIMARY KEY (invoice_id, line_number),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
);

-- 8. PO Allocations Table (Commitments)
CREATE TABLE IF NOT EXISTS po_allocations (
    allocation_id TEXT PRIMARY KEY,
    po_number TEXT NOT NULL,
    po_line_number INTEGER NOT NULL,
    invoice_id TEXT NOT NULL,
    invoice_line_number INTEGER NOT NULL,
    quantity_allocated NUMERIC NOT NULL,
    amount_allocated NUMERIC NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (po_number, po_line_number) REFERENCES po_line_items(po_number, line_number),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
);

-- 9. Immutable Audit Events Table
CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL, -- 'INVOICE', 'PO', 'ALLOCATION', 'SYSTEM'
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,   -- 'INGESTION', 'EXTRACTION', 'VALIDATION', 'HUMAN_CONFIRMATION', 'FALLBACK'
    actor TEXT NOT NULL,        -- 'SYSTEM', 'GEMINI', 'QWEN', 'USER:<username>'
    payload_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invoices_vendor_num ON invoices(vendor_id, invoice_number);
CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON audit_events(entity_type, entity_id);
```

## 2. Transaction Invariants
- When an invoice status transitions to `APPROVED` or `APPROVED_WITH_TOLERANCE`:
  1. `invoices` table record is updated with new status.
  2. `po_line_items.quantity_allocated` is incremented.
  3. Records are inserted into `po_allocations`.
  4. An `audit_events` row is recorded.
  - All four steps execute within an atomic `BEGIN TRANSACTION ... COMMIT` block.
