import sqlite3
from pathlib import Path
from decimal import Decimal
from typing import Optional

def adapt_decimal(val: Decimal) -> str:
    """Format Decimal to exact canonical string."""
    return str(val)

def convert_decimal(raw: bytes) -> Decimal:
    """Parse exact Decimal from database TEXT column."""
    return Decimal(raw.decode("utf-8"))

# Register adapters with sqlite3 module
sqlite3.register_adapter(Decimal, adapt_decimal)
# Do not register a converter for SQLite's generic TEXT type. That causes every
# textual column (PO numbers, statuses, names, etc.) to be parsed as Decimal.
# Monetary values are converted explicitly at repository boundaries.

DDL_STATEMENTS = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- 1. Vendors Master Table
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tax_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    payment_terms TEXT DEFAULT 'NET30',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Purchase Orders Table
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_number TEXT PRIMARY KEY,
    vendor_id TEXT NOT NULL,
    issue_date DATE NOT NULL,
    matching_type TEXT NOT NULL DEFAULT 'THREE_WAY',
    currency TEXT NOT NULL DEFAULT 'INR',
    total_amount TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
);

-- 3. PO Line Items Table
CREATE TABLE IF NOT EXISTS po_line_items (
    po_number TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    sku TEXT NOT NULL,
    description TEXT NOT NULL,
    quantity_ordered TEXT NOT NULL,
    quantity_allocated TEXT NOT NULL DEFAULT '0.00',
    unit_price TEXT NOT NULL,
    tolerance_percent TEXT NOT NULL DEFAULT '0.02',
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
    quantity_received TEXT NOT NULL,
    quantity_invoiced TEXT NOT NULL DEFAULT '0.00',
    receipt_condition TEXT NOT NULL DEFAULT 'GOOD',
    PRIMARY KEY (grn_number, line_number),
    FOREIGN KEY (grn_number) REFERENCES goods_receipt_notes(grn_number) ON DELETE CASCADE
);

-- 6. Invoices Table
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    invoice_number TEXT,
    vendor_id TEXT,
    vendor_name TEXT NOT NULL,
    po_number TEXT,
    invoice_date DATE,
    subtotal TEXT NOT NULL,
    tax_total TEXT NOT NULL DEFAULT '0.00',
    additional_charges TEXT NOT NULL DEFAULT '0.00',
    grand_total TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL,
    decision_reason TEXT,
    raw_document_hash TEXT NOT NULL,
    extraction_provider TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id),
    FOREIGN KEY (po_number) REFERENCES purchase_orders(po_number)
);

-- Partial Unique Index: Strictly prevents multiple APPROVED invoices with identical numbers
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_approved_invoices 
ON invoices(vendor_id, invoice_number) 
WHERE status IN ('APPROVED', 'APPROVED_WITH_TOLERANCE');

-- 7. Invoice Line Items Table
CREATE TABLE IF NOT EXISTS invoice_line_items (
    invoice_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    sku TEXT,
    description TEXT NOT NULL,
    quantity TEXT NOT NULL,
    unit_price TEXT NOT NULL,
    line_total TEXT NOT NULL,
    tax_rate TEXT NOT NULL DEFAULT '0.00',
    tax_amount TEXT DEFAULT '0.00',
    PRIMARY KEY (invoice_id, line_number),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
);

-- 8. PO Allocations Table
CREATE TABLE IF NOT EXISTS po_allocations (
    allocation_id TEXT PRIMARY KEY,
    po_number TEXT NOT NULL,
    po_line_number INTEGER NOT NULL,
    invoice_id TEXT NOT NULL,
    invoice_line_number INTEGER NOT NULL,
    quantity_allocated TEXT NOT NULL,
    amount_allocated TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (po_number, po_line_number) REFERENCES po_line_items(po_number, line_number),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
);

-- 9. Immutable Audit Events Table
CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_documents (
    document_hash TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    document_bytes BLOB NOT NULL,
    extracted_text TEXT NOT NULL DEFAULT '',
    page_count INTEGER NOT NULL DEFAULT 0,
    is_scanned INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS extraction_records (
    extraction_id TEXT PRIMARY KEY,
    document_hash TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    raw_response_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_hash) REFERENCES source_documents(document_hash)
);

-- Immutability Triggers
CREATE TRIGGER IF NOT EXISTS trg_prevent_audit_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'Audit events are strictly immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_audit_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'Audit events are strictly immutable and cannot be deleted.');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_source_document_update
BEFORE UPDATE ON source_documents
BEGIN
    SELECT RAISE(ABORT, 'Source documents are immutable.');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_source_document_delete
BEFORE DELETE ON source_documents
BEGIN
    SELECT RAISE(ABORT, 'Source documents are immutable.');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_extraction_update
BEFORE UPDATE ON extraction_records
BEGIN
    SELECT RAISE(ABORT, 'Raw extraction records are immutable.');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_extraction_delete
BEFORE DELETE ON extraction_records
BEGIN
    SELECT RAISE(ABORT, 'Raw extraction records are immutable.');
END;

CREATE INDEX IF NOT EXISTS idx_invoices_vendor_num ON invoices(vendor_id, invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_hash ON invoices(raw_document_hash);
CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON audit_events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_extraction_records_document ON extraction_records(document_hash);
"""

def init_db(db_path: str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(DDL_STATEMENTS)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(invoice_line_items)")}
        if "tax_rate" not in columns:
            conn.execute(
                "ALTER TABLE invoice_line_items ADD COLUMN tax_rate TEXT NOT NULL DEFAULT '0.00'"
            )

def get_connection(db_path: str) -> sqlite3.Connection:
    init_db(db_path)
    conn = sqlite3.connect(
        db_path,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        timeout=30.0
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

