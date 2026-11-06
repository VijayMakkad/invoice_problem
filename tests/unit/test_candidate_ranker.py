from decimal import Decimal
from datetime import date
from src.engine.candidate_ranker import CandidateRanker
from src.domain.invoice import CanonicalInvoice, InvoiceLineItem
from src.domain.purchase_order import PurchaseOrder, POLineItem
from src.domain.decision import MatchingType

def test_candidate_ranking_exact_scores():
    ranker = CandidateRanker()

    invoice = CanonicalInvoice(
        invoice_number="INV-2024-E2-05",
        vendor_name="Bharat Office Tech Pvt Ltd",
        invoice_date=date(2024, 10, 17),
        purchase_order_number=None,  # Missing PO
        currency="INR",
        subtotal=Decimal("5000.00"),
        tax_total=Decimal("0.00"),
        additional_charges=Decimal("0.00"),
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
        raw_document_hash="dummy_hash_e2",
        extraction_provider="test",
    )

    po1 = PurchaseOrder(
        po_number="PO-2024-008",
        vendor_id="VEND-008",
        vendor_name="Bharat Office Tech Pvt Ltd",
        issue_date=date(2024, 10, 1),
        matching_type=MatchingType.TWO_WAY,
        currency="INR",
        total_amount=Decimal("5000.00"),
        line_items=[
            POLineItem(
                line_number=1,
                sku="HW-DESK-01",
                description="Modular Workstation Desk",
                quantity_ordered=Decimal("5.0"),
                quantity_allocated=Decimal("0.0"),
                unit_price=Decimal("1000.00"),
                tolerance_percent=Decimal("0.02"),
            )
        ]
    )

    po2 = PurchaseOrder(
        po_number="PO-2024-009",
        vendor_id="VEND-008",
        vendor_name="Bharat Office Tech Pvt Ltd",
        issue_date=date(2024, 10, 10),
        matching_type=MatchingType.TWO_WAY,
        currency="INR",
        total_amount=Decimal("10000.00"),
        line_items=[
            POLineItem(
                line_number=1,
                sku="HW-DESK-01",
                description="Modular Workstation Desk",
                quantity_ordered=Decimal("10.0"),
                quantity_allocated=Decimal("0.0"),
                unit_price=Decimal("1000.00"),
                tolerance_percent=Decimal("0.02"),
            )
        ]
    )

    ranked = ranker.rank_candidates(invoice, [po1, po2])

    assert len(ranked) == 2
    # Candidate 1: PO-2024-008 has exact amount match -> Score 1.00
    assert ranked[0].po_number == "PO-2024-008"
    assert ranked[0].score == Decimal("1.00")
    assert "Exact Amount Match" in ranked[0].evidence_summary

    # Candidate 2: PO-2024-009 has partial amount match -> Score 0.90
    assert ranked[1].po_number == "PO-2024-009"
    assert ranked[1].score == Decimal("0.90")
    assert "Partial Amount Match" in ranked[1].evidence_summary

