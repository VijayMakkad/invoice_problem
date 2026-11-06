from decimal import Decimal
from datetime import date
from src.domain.invoice import CanonicalInvoice, InvoiceLineItem

def test_h1_exact_twoway(service):
    inv = CanonicalInvoice(
        invoice_number="INV-2024-H1-01",
        vendor_name="CloudScale IT Solutions Pvt Ltd",
        invoice_date=date(2024, 10, 15),
        purchase_order_number="PO-2024-001",
        currency="INR",
        subtotal=Decimal("150000.00"),
        tax_total=Decimal("0.00"),
        additional_charges=Decimal("0.00"),
        grand_total=Decimal("150000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="SVC-DEV-01",
                description="Cloud DevOps Consulting (Hours)",
                quantity=Decimal("100.00"),
                unit_price=Decimal("1500.00"),
                line_total=Decimal("150000.00"),
            )
        ],
        raw_document_hash="hash_h1_exact",
        extraction_provider="test",
    )
    result = service.process_invoice_document(b"pdf_bytes", "INV-H1-ExactMatch.pdf", provided_invoice=inv)
    assert result["status"] == "APPROVED"
    assert result["allocated_amount"] == Decimal("150000.00")
    assert result["price_variance_percent"] == Decimal("0.00")

def test_h2_tolerance_pass(service):
    # PO: 5 units @ ₹1,000 = ₹5,000 (3% tolerance)
    # Invoice: 5 units @ ₹1,020 = ₹5,100 (+2% variance)
    inv = CanonicalInvoice(
        invoice_number="INV-2024-H2-02",
        vendor_name="Prime Office Supplies Ltd",
        invoice_date=date(2024, 10, 16),
        purchase_order_number="PO-2024-002",
        currency="INR",
        subtotal=Decimal("5100.00"),
        tax_total=Decimal("0.00"),
        additional_charges=Decimal("0.00"),
        grand_total=Decimal("5100.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="HW-OFF-01",
                description="Ergonomic Executive Chair",
                quantity=Decimal("5.00"),
                unit_price=Decimal("1020.00"),
                line_total=Decimal("5100.00"),
            )
        ],
        raw_document_hash="hash_h2_tolerance",
        extraction_provider="test",
    )
    result = service.process_invoice_document(b"pdf_bytes", "INV-H2-TolerancePass.pdf", provided_invoice=inv)
    assert result["status"] == "APPROVED_WITH_TOLERANCE"
    assert result["price_variance_percent"] == Decimal("2.00")
    assert result["allocated_amount"] == Decimal("5100.00")

def test_h3_equivalent_description(service):
    # PO desc: "Dell Latitude 5440 Laptop"
    # Invoice desc: "Dell Latitude 5440"
    # Both share verified SKU DL-5440
    inv = CanonicalInvoice(
        invoice_number="INV-2024-H3-03",
        vendor_name="Dell Computer India Pvt Ltd",
        invoice_date=date(2024, 10, 16),
        purchase_order_number="PO-2024-003",
        currency="INR",
        subtotal=Decimal("650000.00"),
        tax_total=Decimal("0.00"),
        additional_charges=Decimal("0.00"),
        grand_total=Decimal("650000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="DL-5440",
                description="Dell Latitude 5440",
                quantity=Decimal("10.00"),
                unit_price=Decimal("65000.00"),
                line_total=Decimal("650000.00"),
            )
        ],
        raw_document_hash="hash_h3_equiv",
        extraction_provider="test",
    )
    result = service.process_invoice_document(b"pdf_bytes", "INV-H3-EquivalentDesc.pdf", provided_invoice=inv)
    assert result["status"] == "APPROVED"
    assert result["matched_sku"] == "DL-5440"
    assert result["allocated_amount"] == Decimal("650000.00")

