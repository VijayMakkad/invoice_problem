import pytest
import sqlite3
from decimal import Decimal
from src.storage.connection import get_connection
from src.storage.repositories.document_repository import DocumentRepository

def test_decimal_text_roundtrip_adapter(temp_db):
    conn = get_connection(temp_db)
    cursor = conn.cursor()

    # Query PO line with Decimal
    cursor.execute("SELECT unit_price FROM po_line_items WHERE po_number = 'PO-2024-001'")
    row = cursor.fetchone()
    # SQLite stores exact monetary strings; repositories convert explicitly to Decimal.
    assert row["unit_price"] == "1500.00"
    assert Decimal(row["unit_price"]) == Decimal("1500.00")
    conn.close()

def test_audit_immutability_triggers(temp_db):
    conn = get_connection(temp_db)
    cursor = conn.cursor()

    # Insert an audit event
    cursor.execute(
        "INSERT INTO audit_events (event_id, entity_type, entity_id, event_type, actor, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
        ("EV-TEST-01", "INVOICE", "INV-1", "TEST", "SYSTEM", "{}")
    )
    conn.commit()

    # Attempt UPDATE -> must be aborted by trigger
    with pytest.raises(sqlite3.IntegrityError, match="strictly immutable"):
        cursor.execute("UPDATE audit_events SET actor = 'HACKER' WHERE event_id = 'EV-TEST-01'")
        conn.commit()

    # Attempt DELETE -> must be aborted by trigger
    with pytest.raises(sqlite3.IntegrityError, match="strictly immutable"):
        cursor.execute("DELETE FROM audit_events WHERE event_id = 'EV-TEST-01'")
        conn.commit()

    conn.close()

def test_source_and_raw_extraction_immutability(temp_db):
    conn = get_connection(temp_db)
    documents = DocumentRepository(conn)
    documents.store_source(
        document_hash="source-hash-01",
        filename="invoice.pdf",
        mime_type="application/pdf",
        document_bytes=b"%PDF-test",
        extracted_text="Invoice contents",
        page_count=1,
        is_scanned=False,
    )
    extraction_id = documents.record_extraction(
        document_hash="source-hash-01",
        provider_name="gemini",
        latency_ms=100,
        prompt_tokens=10,
        completion_tokens=20,
        raw_response_text='{"invoice_number":"INV-1"}',
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError, match="Source documents are immutable"):
        conn.execute("UPDATE source_documents SET filename = 'changed.pdf' WHERE document_hash = 'source-hash-01'")
    with pytest.raises(sqlite3.IntegrityError, match="Raw extraction records are immutable"):
        conn.execute("DELETE FROM extraction_records WHERE extraction_id = ?", (extraction_id,))
    conn.close()

def test_partial_unique_index_approved_duplicates(temp_db):
    conn = get_connection(temp_db)
    cursor = conn.cursor()

    # Insert first approved invoice
    cursor.execute(
        """
        INSERT INTO invoices (invoice_id, invoice_number, vendor_id, vendor_name, subtotal, grand_total, status, raw_document_hash, extraction_provider)
        VALUES ('INV-TEST-A1', 'INV-UNIQUE-01', 'VEND-001', 'CloudScale', '1000.00', '1000.00', 'APPROVED', 'hash_a1', 'test')
        """
    )
    conn.commit()

    # Attempt to insert second APPROVED invoice with identical vendor and number -> fails partial unique index
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            """
            INSERT INTO invoices (invoice_id, invoice_number, vendor_id, vendor_name, subtotal, grand_total, status, raw_document_hash, extraction_provider)
            VALUES ('INV-TEST-A2', 'INV-UNIQUE-01', 'VEND-001', 'CloudScale', '1000.00', '1000.00', 'APPROVED', 'hash_a2', 'test')
            """
        )
        conn.commit()

    # Inserting a BLOCKED invoice with identical vendor and number -> SUCCEEDS (allows audit explainability)
    cursor.execute(
        """
        INSERT INTO invoices (invoice_id, invoice_number, vendor_id, vendor_name, subtotal, grand_total, status, raw_document_hash, extraction_provider)
        VALUES ('INV-TEST-A3', 'INV-UNIQUE-01', 'VEND-001', 'CloudScale', '1000.00', '1000.00', 'BLOCKED', 'hash_a3', 'test')
        """
    )
    conn.commit()
    conn.close()

