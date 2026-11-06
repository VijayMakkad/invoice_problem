from decimal import Decimal
from typing import Optional, Tuple
from src.domain.invoice import InvoiceLineItem
from src.domain.purchase_order import PurchaseOrder, POLineItem

class MatchingEngine:
    """
    Handles SKU normalization, description compatibility checks,
    and priority matching rules between invoice lines and PO lines.
    """
    @staticmethod
    def match_line_item(invoice_line: InvoiceLineItem, po: PurchaseOrder) -> Tuple[Optional[POLineItem], Optional[str]]:
        """
        Matches an invoice line to a PO line.
        Priority:
        1. Exact SKU match takes absolute precedence.
        2. Verified SKU match overrides minor description differences.
        3. Conflicting SKU must never pass.
        Returns (matched_po_line, mismatch_reason)
        """
        inv_sku = invoice_line.sku.strip().upper() if invoice_line.sku else None
        inv_desc = invoice_line.description.strip().lower()

        # Step A: Direct SKU Lookup
        if inv_sku:
            po_line = po.get_line_by_sku(inv_sku)
            if po_line:
                # Verified SKU found!
                return po_line, None
            else:
                return None, f"SKU '{invoice_line.sku}' is not authorized on PO {po.po_number}."

        # Step B: If SKU is missing from invoice line, attempt high-confidence description match
        for line in po.line_items:
            po_desc = line.description.strip().lower()
            if inv_desc in po_desc or po_desc in inv_desc:
                return line, None

        return None, f"Item '{invoice_line.description}' could not be mapped to any line on PO {po.po_number}."

