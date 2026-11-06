# Goods Received Note (GRN) Schema Specification

This document defines the schema and matching invariants for warehouse receiving documents (GRNs).

## 1. GRN Data Structure

```python
from decimal import Decimal
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

class GRNLineItem(BaseModel):
    line_number: int = Field(..., description="1-based index on GRN")
    po_line_number: int = Field(..., description="Referenced PO line number")
    sku: str = Field(..., min_length=1, description="Product SKU received")
    quantity_received: Decimal = Field(..., gt=0, description="Quantity verified by warehouse")
    quantity_invoiced: Decimal = Field(Decimal("0.00"), ge=0, description="Cumulative quantity already matched against invoices")
    receipt_condition: str = Field("GOOD", description="GOOD, DAMAGED, or SHORT")

    @property
    def unbilled_quantity(self) -> Decimal:
        return self.quantity_received - self.quantity_invoiced

class GoodsReceiptNote(BaseModel):
    grn_number: str = Field(..., min_length=1, description="Receipt number (e.g. GRN-2024-002)")
    po_number: str = Field(..., min_length=1, description="Purchase order reference")
    vendor_name: str = Field(..., min_length=1, description="Supplier name delivering goods")
    received_date: date = Field(..., description="Date shipment was accepted at warehouse")
    received_by: str = Field(..., description="Staff member who inspected delivery")
    line_items: List[GRNLineItem] = Field(..., min_length=1)
```

## 2. Invariants & Matching Logic
- **Three-Way Matching**:
  - The invoice SKU must match the GRN SKU.
  - The invoice quantity must be $\le$ `unbilled_quantity` on the GRN.
  - If invoice quantity exceeds `unbilled_quantity`, the validation engine flags a partial delivery variance and places the invoice on `HOLD_FOR_REVIEW`.
- If an invoice requires 3-way matching and no GRN is found in the database, the invoice is set to `HOLD_FOR_REVIEW` with the reason `"Missing Goods Received Note (GRN)"`.
