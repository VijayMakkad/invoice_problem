# Purchase Order Schema Specification

This document defines the Purchase Order (PO) data model used in Zamp ASA procurement records.

## 1. Purchase Order Data Structure

```python
from decimal import Decimal
from datetime import date
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class MatchingType(str, Enum):
    TWO_WAY = "TWO_WAY"       # Invoice vs PO (Services / Software)
    THREE_WAY = "THREE_WAY"   # Invoice vs PO vs GRN (Physical Goods)

class POLineItem(BaseModel):
    line_number: int = Field(..., description="1-based line number on PO")
    sku: str = Field(..., min_length=1, description="Unique product SKU or service code")
    description: str = Field(..., description="Item description")
    quantity_ordered: Decimal = Field(..., gt=0, description="Total authorized quantity")
    quantity_allocated: Decimal = Field(Decimal("0.00"), ge=0, description="Cumulative quantity approved on prior invoices")
    unit_price: Decimal = Field(..., ge=0, description="Contracted unit price")
    line_total: Decimal = Field(..., ge=0, description="quantity_ordered * unit_price")
    tolerance_percent: Decimal = Field(Decimal("0.02"), ge=0, description="Allowed price variance (default 2%)")

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity_ordered - self.quantity_allocated

class PurchaseOrder(BaseModel):
    po_number: str = Field(..., min_length=1, description="Unique identifier (e.g. PO-2024-001)")
    vendor_name: str = Field(..., min_length=1, description="Authorized supplier name")
    vendor_tax_id: Optional[str] = Field(None, description="Supplier tax ID / VAT number")
    issue_date: date = Field(..., description="Date PO was authorized")
    status: str = Field("ACTIVE", description="ACTIVE, CLOSED, or CANCELLED")
    matching_type: MatchingType = Field(MatchingType.THREE_WAY, description="TWO_WAY or THREE_WAY")
    currency: str = Field("USD", min_length=3, max_length=3)
    total_amount: Decimal = Field(..., ge=0, description="Total contracted amount")
    line_items: List[POLineItem] = Field(..., min_length=1)
```

## 2. Invariants
- A PO with `matching_type == MatchingType.THREE_WAY` mandates a corresponding Goods Received Note (GRN) before approval.
- An invoice line must never consume more than `remaining_quantity` unless a formal PO change order is registered.
- Allocations are incremented only upon `APPROVED` or `APPROVED_WITH_TOLERANCE` status.
