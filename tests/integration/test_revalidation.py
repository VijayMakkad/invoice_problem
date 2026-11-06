from decimal import Decimal
from datetime import date
import pytest
from src.storage.connection import get_connection
from src.storage.repositories.po_repository import PORepository
from src.domain.invoice import CanonicalInvoice, InvoiceLineItem
from src.services.invoice_service import InvoiceProcessingService

def test_missing_po_human_confirmation_revalidation(service):
    # Invoice without PO number
    inv = CanonicalInvoice(
        invoice_number="INV-REVAL-01",
        vendor_name="Bharat Office Tech Pvt Ltd",
        invoice_date=date(2024, 10, 17),
        purchase_order_number=None,  # Missing PO
        currency="INR",
        subtotal=Decimal("5000.00"),
        grand_total=Decimal("5000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="HW-DESK-01",
                description="Modular Workstation Desk",
                quantity=Decimal("5.0"),
                unit_price=Decimal("1000.00"),
                line_total=Decimal("5000.00"),
            )
        ],
        raw_document_hash="reval_test_hash_01",
        extraction_provider="test",
    )

    res1 = service.process_invoice_document(b"pdf_bytes", "invoice.pdf", provided_invoice=inv)
    assert res1["status"] == "PENDING_CONFIRMATION"
    assert res1["requires_human_action"] is True
    assert res1["action_type"] == "PO_SELECTION"

    # Human selects candidate PO-2024-008
    invoice_id = res1["invoice_id"]
    res2 = service.confirm_po_selection(invoice_id, "PO-2024-008")

    assert res2["status"] == "APPROVED"
    assert res2["allocated_amount"] == Decimal("5000.00")

    with get_connection(service.db_path) as conn:
        allocated_once = PORepository(conn).get_by_number("PO-2024-008").line_items[0].quantity_allocated
    with pytest.raises(ValueError, match="only allowed for invoices pending confirmation"):
        service.confirm_po_selection(invoice_id, "PO-2024-008")
    with get_connection(service.db_path) as conn:
        allocated_twice = PORepository(conn).get_by_number("PO-2024-008").line_items[0].quantity_allocated
    assert allocated_twice == allocated_once

def test_bundle_decomposition_human_confirmation_revalidation(service):
    # Invoice with bundled Accessory Kit
    inv = CanonicalInvoice(
        invoice_number="INV-REVAL-BUNDLE-02",
        vendor_name="Nordic Peripheral Systems",
        invoice_date=date(2024, 10, 18),
        purchase_order_number="PO-2024-005",
        currency="INR",
        subtotal=Decimal("3000.00"),
        grand_total=Decimal("3000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="KIT-ACC-01",
                description="Accessory Kit",
                quantity=Decimal("1.0"),
                unit_price=Decimal("3000.00"),
                line_total=Decimal("3000.00"),
            )
        ],
        raw_document_hash="reval_test_hash_02",
        extraction_provider="test",
    )

    res1 = service.process_invoice_document(b"pdf_bytes", "invoice.pdf", provided_invoice=inv)
    assert res1["status"] == "PENDING_CONFIRMATION"
    assert res1["action_type"] == "BUNDLE_CONFIRMATION"

    # Human accepts bundle decomposition
    invoice_id = res1["invoice_id"]
    res2 = service.confirm_bundle_decomposition(invoice_id)

    assert res2["status"] == "APPROVED"
    assert res2["allocated_amount"] == Decimal("3000.00")


def test_audited_field_correction_reruns_full_validation(service):
    invoice = CanonicalInvoice(
        invoice_number="INV-CORRECTION-01",
        vendor_name="Bharat Office Tech Pvt Ltd",
        invoice_date=date(2024, 10, 17),
        purchase_order_number=None,
        currency="INR",
        subtotal=Decimal("5000.00"),
        grand_total=Decimal("5000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="HW-DESK-01",
                description="Modular Workstation Desk",
                quantity=Decimal("5.00"),
                unit_price=Decimal("1000.00"),
                line_total=Decimal("5000.00"),
            )
        ],
        raw_document_hash="correction-source-hash",
        extraction_provider="test",
    )
    pending = service.process_invoice_document(b"correction-file", "invoice.pdf", provided_invoice=invoice)
    assert pending["status"] == "PENDING_CONFIRMATION"

    corrected = invoice.model_copy(update={"purchase_order_number": "PO-2024-008"})
    result = service.revalidate_invoice(pending["invoice_id"], corrected, actor="USER:test")
    assert result["status"] == "APPROVED"

    events = service.list_recent_audit_events()
    correction_events = [event for event in events if event["event_type"] == "HUMAN_CORRECTION"]
    assert correction_events
    assert correction_events[0]["actor"] == "USER:test"

