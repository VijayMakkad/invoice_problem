from decimal import Decimal
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

class GRNLineItem(BaseModel):
    line_number: int = Field(..., description="1-based line number on GRN")
    po_line_number: int = Field(..., description="Referenced PO line number")
    sku: str = Field(..., min_length=1, description="Received product SKU")
    quantity_received: Decimal = Field(..., gt=0, description="Quantity verified by warehouse")
    quantity_invoiced: Decimal = Field(Decimal("0.00"), ge=0, description="Cumulative quantity billed")
    receipt_condition: str = Field(default="GOOD")  # GOOD, DAMAGED, SHORT

    @property
    def unbilled_quantity(self) -> Decimal:
        return self.quantity_received - self.quantity_invoiced

class GoodsReceiptNote(BaseModel):
    grn_number: str = Field(..., min_length=1)
    po_number: str = Field(..., min_length=1)
    vendor_name: str = Field(..., min_length=1)
    received_date: date
    received_by: str = Field(..., min_length=1)
    line_items: List[GRNLineItem] = Field(..., min_length=1)

    def get_line_by_sku(self, sku: str) -> Optional[GRNLineItem]:
        for line in self.line_items:
            if line.sku.strip().upper() == sku.strip().upper():
                return line
        return None

