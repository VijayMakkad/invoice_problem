from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field
from src.domain.decision import MatchingType

class POLineItem(BaseModel):
    line_number: int = Field(..., description="1-based line number on PO")
    sku: str = Field(..., min_length=1, description="Product SKU or service code")
    description: str = Field(..., description="Item contracted description")
    quantity_ordered: Decimal = Field(..., gt=0, description="Total contracted quantity")
    quantity_allocated: Decimal = Field(Decimal("0.00"), ge=0, description="Cumulative quantity approved")
    unit_price: Decimal = Field(..., ge=0, description="Contracted unit price")
    tolerance_percent: Decimal = Field(Decimal("0.02"), ge=0, description="Authorized variance (e.g. 0.02 for 2%)")

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity_ordered - self.quantity_allocated

    @property
    def base_line_total(self) -> Decimal:
        return (self.quantity_ordered * self.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def remaining_line_total(self) -> Decimal:
        return (self.remaining_quantity * self.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def tolerance_ceiling(self) -> Decimal:
        """Maximum allowable line expenditure with authorized price tolerance."""
        return (self.remaining_quantity * self.unit_price * (Decimal("1.0") + self.tolerance_percent)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

class PurchaseOrder(BaseModel):
    po_number: str = Field(..., min_length=1)
    vendor_id: str = Field(..., min_length=1)
    vendor_name: str = Field(..., min_length=1)
    vendor_tax_id: Optional[str] = None
    issue_date: date
    matching_type: MatchingType = Field(default=MatchingType.THREE_WAY)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    total_amount: Decimal = Field(..., ge=0)
    status: str = Field(default="ACTIVE")  # ACTIVE, CLOSED, CANCELLED
    line_items: List[POLineItem] = Field(..., min_length=1)

    def get_line_by_sku(self, sku: str) -> Optional[POLineItem]:
        for line in self.line_items:
            if line.sku.strip().upper() == sku.strip().upper():
                return line
        return None

    @property
    def total_allocated_amount(self) -> Decimal:
        return sum((l.quantity_allocated * l.unit_price for l in self.line_items), Decimal("0.00")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def remaining_budget(self) -> Decimal:
        return (self.total_amount - self.total_allocated_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_tolerance_ceiling(self) -> Decimal:
        return sum((l.tolerance_ceiling for l in self.line_items), Decimal("0.00")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

