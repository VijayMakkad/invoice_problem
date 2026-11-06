from decimal import Decimal
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from src.domain.invoice import CanonicalInvoice
from src.domain.purchase_order import PurchaseOrder

class RankedCandidate(BaseModel):
    po_number: str
    vendor_id: str
    vendor_name: str
    score: Decimal
    vendor_match_score: Decimal
    sku_match_score: Decimal
    amount_similarity_score: Decimal
    currency_match_score: Decimal
    remaining_budget: Decimal
    total_amount: Decimal
    evidence_summary: str

class CandidateRanker:
    """
    Ranks open PO candidates when an invoice omits the PO reference.
    Uses multi-factor evidence-based weighted scoring formula:
      Score = w_vendor * S_vendor + w_sku * S_sku + w_amount * S_amount + w_currency * S_currency
      Weights: w_vendor=0.35, w_sku=0.35, w_amount=0.20, w_currency=0.10
    """
    def __init__(
        self,
        w_vendor: Decimal = Decimal("0.35"),
        w_sku: Decimal = Decimal("0.35"),
        w_amount: Decimal = Decimal("0.20"),
        w_currency: Decimal = Decimal("0.10"),
        min_threshold: Decimal = Decimal("0.50"),
    ):
        self.w_vendor = w_vendor
        self.w_sku = w_sku
        self.w_amount = w_amount
        self.w_currency = w_currency
        self.min_threshold = min_threshold

    def rank_candidates(
        self,
        invoice: CanonicalInvoice,
        open_pos: List[PurchaseOrder]
    ) -> List[RankedCandidate]:
        results: List[RankedCandidate] = []
        inv_skus = {line.sku.strip().upper() for line in invoice.line_items if line.sku}

        for po in open_pos:
            # 1. Vendor Match Score
            s_vendor = Decimal("1.0") if po.vendor_name.strip().lower() in invoice.vendor_name.strip().lower() or invoice.vendor_name.strip().lower() in po.vendor_name.strip().lower() else Decimal("0.0")

            # 2. SKU Overlap Score
            po_skus = {line.sku.strip().upper() for line in po.line_items}
            if inv_skus:
                overlap = len(inv_skus.intersection(po_skus))
                s_sku = Decimal(overlap) / Decimal(len(inv_skus))
            else:
                s_sku = Decimal("0.5")  # Neutral if no SKUs to compare

            # 3. Amount Similarity Score
            # S_amount = max(0, 1 - |Invoice_Subtotal - PO_Remaining_Value| / PO_Total_Amount)
            diff = abs(invoice.subtotal - po.remaining_budget)
            if po.total_amount > Decimal("0.00"):
                ratio = diff / po.total_amount
                s_amount = max(Decimal("0.00"), Decimal("1.00") - ratio)
            else:
                s_amount = Decimal("0.00")

            # 4. Currency Match Score
            s_currency = Decimal("1.0") if invoice.currency.strip().upper() == po.currency.strip().upper() else Decimal("0.0")

            # Total Weighted Score
            total_score = (
                self.w_vendor * s_vendor +
                self.w_sku * s_sku +
                self.w_amount * s_amount +
                self.w_currency * s_currency
            ).quantize(Decimal("0.01"))

            if total_score >= self.min_threshold:
                evidence = []
                if s_vendor == Decimal("1.0"):
                    evidence.append("Vendor Identity Match")
                if s_sku == Decimal("1.0"):
                    evidence.append("Full SKU Match")
                elif s_sku > Decimal("0.0"):
                    evidence.append(f"Partial SKU Match ({int(s_sku*100)}%)")
                
                if s_amount == Decimal("1.0"):
                    evidence.append(f"Exact Amount Match (₹{invoice.subtotal} / ₹{po.remaining_budget})")
                else:
                    evidence.append(f"Partial Amount Match (₹{invoice.subtotal} vs remaining ₹{po.remaining_budget})")

                results.append(
                    RankedCandidate(
                        po_number=po.po_number,
                        vendor_id=po.vendor_id,
                        vendor_name=po.vendor_name,
                        score=total_score,
                        vendor_match_score=s_vendor,
                        sku_match_score=s_sku,
                        amount_similarity_score=s_amount.quantize(Decimal("0.01")),
                        currency_match_score=s_currency,
                        remaining_budget=po.remaining_budget,
                        total_amount=po.total_amount,
                        evidence_summary=", ".join(evidence)
                    )
                )

        # Sort descending by score
        results.sort(key=lambda c: c.score, reverse=True)
        return results

