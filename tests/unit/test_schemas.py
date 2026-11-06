import pytest
from decimal import Decimal
from datetime import date
from src.domain.invoice import CanonicalInvoice, InvoiceLineItem
from src.domain.purchase_order import PurchaseOrder, POLineItem
from src.domain.goods_receipt import GoodsReceiptNote, GRNLineItem
from src.domain.decision import MatchingType, DecisionStatus

def test_canonical_schema_compliance():
    line = InvoiceLineItem(
        line_number=1,
        sku="TEST-SKU-01",
        description="Test Item Description",
        quantity=Decimal("10.00"),
        unit_price=Decimal("150.00"),
        line_total=Decimal("1500.00"),
        tax_rate=Decimal("0.18"),
        tax_amount=Decimal("270.00"),
    )
    inv = CanonicalInvoice(
        invoice_number="INV-TEST-001",
        vendor_name="Acme Supplies Ltd",
        invoice_date=date(2024, 10, 15),
        currency="INR",
        subtotal=Decimal("1500.00"),
        tax_total=Decimal("270.00"),
        additional_charges=Decimal("0.00"),
        grand_total=Decimal("1770.00"),
        line_items=[line],
        raw_document_hash="test_sha256_hash",
        extraction_provider="test_provider",
    )
    assert inv.grand_total == Decimal("1770.00")
    assert isinstance(inv.subtotal, Decimal)

def test_line_item_arithmetic_validation():
    with pytest.raises(ValueError, match="Line total"):
        InvoiceLineItem(
            line_number=1,
            sku="SKU-ERR",
            description="Bad Math Item",
            quantity=Decimal("10.00"),
            unit_price=Decimal("150.00"),
            line_total=Decimal("2000.00"),  # Error! Should be 1500.00
        )

def test_header_grand_total_validation():
    line = InvoiceLineItem(
        line_number=1,
        sku="SKU-01",
        description="Valid Line",
        quantity=Decimal("1.00"),
        unit_price=Decimal("100.00"),
        line_total=Decimal("100.00"),
    )
    with pytest.raises(ValueError, match="Grand total"):
        CanonicalInvoice(
            invoice_number="INV-BAD-TOTAL",
            vendor_name="Acme",
            invoice_date=date(2024, 10, 15),
            subtotal=Decimal("100.00"),
            tax_total=Decimal("18.00"),
            additional_charges=Decimal("0.00"),
            grand_total=Decimal("500.00"),  # Error! Should be 118.00
            line_items=[line],
            raw_document_hash="hash",
            extraction_provider="test",
        )

