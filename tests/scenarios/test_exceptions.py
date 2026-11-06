from decimal import Decimal
from datetime import date
from src.domain.invoice import CanonicalInvoice, InvoiceLineItem

def test_e1_overbilling_hold(service):
    # PO-2024-004: ₹1,00,000 limit. Seeded prior allocation: ₹70,000. Remaining: ₹30,000.
    # Incoming invoice: ₹80,000 -> Excess: ₹50,000
    inv = CanonicalInvoice(
        invoice_number="INV-2024-E1-04",
        vendor_name="Apex Industrial Tools Corp",
        invoice_date=date(2024, 10, 17),
        purchase_order_number="PO-2024-004",
        currency="INR",
        subtotal=Decimal("80000.00"),
        tax_total=Decimal("0.00"),
        additional_charges=Decimal("0.00"),
        grand_total=Decimal("80000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="IND-TOOL-01",
                description="Precision CNC Mill Cutters",
                quantity=Decimal("80.00"),
                unit_price=Decimal("1000.00"),
                line_total=Decimal("80000.00"),
            )
        ],
        raw_document_hash="hash_e1_overbilling",
        extraction_provider="test",
    )
    result = service.process_invoice_document(b"pdf_bytes", "INV-E1-Overbilling.pdf", provided_invoice=inv)
    assert result["status"] == "HOLD_FOR_REVIEW"
    assert result["excess_budget"] == Decimal("50000.00")
    assert result["remaining_budget"] == Decimal("30000.00")
    assert result["allocated_amount"] == Decimal("0.00")

def test_e2_missing_po_candidate_ranking(service):
    inv = CanonicalInvoice(
        invoice_number="INV-2024-E2-05",
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
        raw_document_hash="hash_e2_missing_po",
        extraction_provider="test",
    )
    result = service.process_invoice_document(b"pdf_bytes", "INV-E2-MissingPO.pdf", provided_invoice=inv)
    assert result["status"] == "PENDING_CONFIRMATION"
    assert result["requires_human_action"] is True
    assert result["action_type"] == "PO_SELECTION"

    # Human selects candidate PO-2024-008
    reval = service.confirm_po_selection(result["invoice_id"], "PO-2024-008")
    assert reval["status"] == "APPROVED"
    assert reval["allocated_amount"] == Decimal("5000.00")

def test_e3_bundle_decomposition(service):
    inv = CanonicalInvoice(
        invoice_number="INV-2024-E3-06",
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
        raw_document_hash="hash_e3_bundle",
        extraction_provider="test",
    )
    result = service.process_invoice_document(b"pdf_bytes", "INV-E3-BundleKit.pdf", provided_invoice=inv)
    assert result["status"] == "PENDING_CONFIRMATION"
    assert result["action_type"] == "BUNDLE_CONFIRMATION"

    reval = service.confirm_bundle_decomposition(result["invoice_id"])
    assert reval["status"] == "APPROVED"
    assert reval["allocated_amount"] == Decimal("3000.00")

def test_e4_tax_and_additional_delivery_charge(service):
    # Base ₹1,000 + 18% GST ₹180 + Unapproved Delivery Fee ₹500 = ₹1,680
    inv = CanonicalInvoice(
        invoice_number="INV-2024-E4-07",
        vendor_name="Global Logistics & Packaging",
        invoice_date=date(2024, 10, 18),
        purchase_order_number="PO-2024-006",
        currency="INR",
        subtotal=Decimal("1000.00"),
        tax_total=Decimal("180.00"),
        additional_charges=Decimal("500.00"),
        grand_total=Decimal("1680.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="MAT-BOX-01",
                description="Heavy Duty Packing Cartons",
                quantity=Decimal("1.00"),
                unit_price=Decimal("1000.00"),
                line_total=Decimal("1000.00"),
                tax_rate=Decimal("0.18"),
                tax_amount=Decimal("180.00"),
            )
        ],
        raw_document_hash="hash_e4_tax_fee",
        extraction_provider="test",
    )
    result = service.process_invoice_document(b"pdf_bytes", "INV-E4-TaxDeliveryFee.pdf", provided_invoice=inv)
    assert result["status"] == "HOLD_FOR_REVIEW"
    assert "Unapproved additional charge of ₹500" in result["primary_reason"]
    assert result["allocated_amount"] == Decimal("0.00")

def test_e5_short_receipt_amount(service):
    # PO-2024-007: 10 laptops @ ₹50,000 = ₹5,00,000. GRN accepted only 7.
    inv = CanonicalInvoice(
        invoice_number="INV-2024-E5-08",
        vendor_name="Precision Tech Systems Ltd",
        invoice_date=date(2024, 10, 19),
        purchase_order_number="PO-2024-007",
        currency="INR",
        subtotal=Decimal("500000.00"),
        tax_total=Decimal("0.00"),
        additional_charges=Decimal("0.00"),
        grand_total=Decimal("500000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="NB-PRO-15",
                description="Enterprise Commercial Laptop",
                quantity=Decimal("10.00"),
                unit_price=Decimal("50000.00"),
                line_total=Decimal("500000.00"),
            )
        ],
        raw_document_hash="hash_e5_short_receipt",
        extraction_provider="test",
    )
    result = service.process_invoice_document(b"pdf_bytes", "INV-E5-ShortReceipt.pdf", provided_invoice=inv)
    assert result["status"] == "HOLD_FOR_REVIEW"
    assert "Short delivery receipt" in result["primary_reason"]
    assert result["allocated_amount"] == Decimal("0.00")

def test_edup_identical_replay_idempotency(service):
    inv = CanonicalInvoice(
        invoice_number="INV-REPLAY-01",
        vendor_name="CloudScale IT Solutions Pvt Ltd",
        invoice_date=date(2024, 10, 15),
        purchase_order_number="PO-2024-001",
        currency="INR",
        subtotal=Decimal("150000.00"),
        grand_total=Decimal("150000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="SVC-DEV-01",
                description="Cloud DevOps Consulting",
                quantity=Decimal("100.00"),
                unit_price=Decimal("1500.00"),
                line_total=Decimal("150000.00"),
            )
        ],
        raw_document_hash="fixed_identical_hash_123",
        extraction_provider="test",
    )
    # First upload
    res1 = service.process_invoice_document(b"dummy_bytes_123", "invoice.pdf", provided_invoice=inv)
    assert res1["status"] == "APPROVED"
    assert res1["is_replay"] is False

    # Second upload with identical bytes/hash
    res2 = service.process_invoice_document(b"dummy_bytes_123", "invoice.pdf", provided_invoice=inv)
    assert res2["is_replay"] is True
    assert res2["status"] == "APPROVED"
    assert res2["allocated_amount"] == Decimal("0.00")  # Zero incremental allocation

def test_edup_duplicate_invoice_number_fraud_block(service):
    inv1 = CanonicalInvoice(
        invoice_number="INV-DUP-FRAUD-01",
        vendor_name="CloudScale IT Solutions Pvt Ltd",
        invoice_date=date(2024, 10, 15),
        purchase_order_number="PO-2024-001",
        currency="INR",
        subtotal=Decimal("150000.00"),
        grand_total=Decimal("150000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="SVC-DEV-01",
                description="Cloud DevOps Consulting",
                quantity=Decimal("100.00"),
                unit_price=Decimal("1500.00"),
                line_total=Decimal("150000.00"),
            )
        ],
        raw_document_hash="first_file_hash_aaa",
        extraction_provider="test",
    )
    res1 = service.process_invoice_document(b"file_aaa", "invoice.pdf", provided_invoice=inv1)
    assert res1["status"] == "APPROVED"

    # Second upload: Same invoice number and vendor, but DIFFERENT document hash
    inv2 = CanonicalInvoice(
        invoice_number="INV-DUP-FRAUD-01",
        vendor_name="CloudScale IT Solutions Pvt Ltd",
        invoice_date=date(2024, 10, 15),
        purchase_order_number="PO-2024-001",
        currency="INR",
        subtotal=Decimal("150000.00"),
        grand_total=Decimal("150000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="SVC-DEV-01",
                description="Cloud DevOps Consulting",
                quantity=Decimal("100.00"),
                unit_price=Decimal("1500.00"),
                line_total=Decimal("150000.00"),
            )
        ],
        raw_document_hash="second_file_hash_bbb",  # Different hash!
        extraction_provider="test",
    )
    res2 = service.process_invoice_document(b"file_bbb", "invoice_altered.pdf", provided_invoice=inv2)
    assert res2["status"] == "BLOCKED"
    assert "Duplicate invoice submission" in res2["primary_reason"]
    assert res2["allocated_amount"] == Decimal("0.00")

def test_evend_unknown_vendor_blocked(service):
    inv = CanonicalInvoice(
        invoice_number="INV-GHOST-01",
        vendor_name="Ghost Vendor LLC",  # Not in master registry
        invoice_date=date(2024, 10, 20),
        purchase_order_number="PO-2024-999",
        currency="INR",
        subtotal=Decimal("25000.00"),
        grand_total=Decimal("25000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="UNREG-01",
                description="Advisory Services",
                quantity=Decimal("1.0"),
                unit_price=Decimal("25000.00"),
                line_total=Decimal("25000.00"),
            )
        ],
        raw_document_hash="hash_ghost_vendor",
        extraction_provider="test",
    )
    result = service.process_invoice_document(b"pdf_bytes", "INV-EVend-Unknown.pdf", provided_invoice=inv)
    assert result["status"] == "BLOCKED"
    assert "Unregistered or inactive vendor" in result["primary_reason"]
    assert result["allocated_amount"] == Decimal("0.00")
    # Verify stored with vendor_id = None
    saved = result["invoice_record"]
    assert saved["vendor_id"] is None

