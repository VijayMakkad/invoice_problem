from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
from src.domain.invoice import InvoiceLineItem
from src.domain.purchase_order import PurchaseOrder

class BundleItemDecomposition(BaseModel):
    bundle_name: str
    target_po_number: str
    decomposed_lines: List[InvoiceLineItem]
    total_amount: Decimal
    is_ambiguous: bool = False
    message: str

class BundleEngine:
    """
    Detects bundled items on supplier invoices and proposes itemized
    decompositions against contracted PO lines.
    """
    # Explicit bundle catalog / aliases
    BUNDLE_CATALOG = {
        "ACCESSORY KIT": [
            {"sku": "KB-01", "description": "Mechanical Office Keyboard", "unit_price": Decimal("2000.00"), "qty": Decimal("1.0")},
            {"sku": "MS-01", "description": "Ergonomic Optical Mouse", "unit_price": Decimal("1000.00"), "qty": Decimal("1.0")},
        ],
        "WORKSTATION COMBO": [
            {"sku": "KB-01", "description": "Mechanical Office Keyboard", "unit_price": Decimal("2000.00"), "qty": Decimal("1.0")},
            {"sku": "MS-01", "description": "Ergonomic Optical Mouse", "unit_price": Decimal("1000.00"), "qty": Decimal("1.0")},
        ]
    }

    def detect_and_decompose(
        self,
        line: InvoiceLineItem,
        po: PurchaseOrder
    ) -> Optional[BundleItemDecomposition]:
        desc_clean = line.description.strip().upper()
        matched_catalog_key = None
        for key in self.BUNDLE_CATALOG:
            if key in desc_clean:
                matched_catalog_key = key
                break

        if not matched_catalog_key:
            return None

        components = self.BUNDLE_CATALOG[matched_catalog_key]
        decomposed_lines: List[InvoiceLineItem] = []
        total_bundle_cost = Decimal("0.00")

        po_skus = {l.sku.strip().upper(): l for l in po.line_items}
        
        # Verify all bundle components exist on the referenced PO
        all_skus_on_po = True
        for comp in components:
            sku = comp["sku"]
            if sku not in po_skus:
                all_skus_on_po = False
                break

        if not all_skus_on_po:
            return BundleItemDecomposition(
                bundle_name=line.description,
                target_po_number=po.po_number,
                decomposed_lines=[],
                total_amount=line.line_total,
                is_ambiguous=True,
                message=f"Bundle '{line.description}' contains items not authorized on PO {po.po_number}"
            )

        # Build proposed decomposed lines
        for idx, comp in enumerate(components, start=1):
            comp_qty = (comp["qty"] * line.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            comp_price = comp["unit_price"]
            comp_total = (comp_qty * comp_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_bundle_cost += comp_total

            decomposed_lines.append(
                InvoiceLineItem(
                    line_number=idx,
                    sku=comp["sku"],
                    description=comp["description"],
                    quantity=comp_qty,
                    unit_price=comp_price,
                    line_total=comp_total,
                    tax_rate=line.tax_rate or Decimal("0.00"),
                    tax_amount=(comp_total * (line.tax_rate or Decimal("0.00"))).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    ),
                )
            )

        # Verify math matches invoice line total
        if total_bundle_cost != line.line_total:
            return BundleItemDecomposition(
                bundle_name=line.description,
                target_po_number=po.po_number,
                decomposed_lines=[],
                total_amount=line.line_total,
                is_ambiguous=True,
                message=f"Bundle decomposition total ₹{total_bundle_cost} does not match billed line total ₹{line.line_total}"
            )

        return BundleItemDecomposition(
            bundle_name=line.description,
            target_po_number=po.po_number,
            decomposed_lines=decomposed_lines,
            total_amount=total_bundle_cost,
            is_ambiguous=False,
            message=f"Propose decomposing '{line.description}' into KB-01 (₹2,000.00) and MS-01 (₹1,000.00)"
        )

