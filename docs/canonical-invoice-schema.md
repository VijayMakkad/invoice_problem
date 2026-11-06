# Canonical Invoice Schema Specification

This document defines the universal JSON/Pydantic representation that all AI extraction providers (Gemini, Qwen) and backend validation engines must conform to.

## 1. Pydantic v2 Model Definition

```python
from decimal import Decimal
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class InvoiceLineItem(BaseModel):
    line_number: int = Field(description="1-based index of item on the invoice")
    sku: Optional[str] = Field(None, description="Item code or product SKU")
    description: str = Field(..., description="Description of product or service")
    quantity: Decimal = Field(..., gt=0, description="Quantity billed")
    unit_price: Decimal = Field(..., ge=0, description="Price per single unit")
    line_total: Decimal = Field(..., ge=0, description="Total cost (quantity * unit_price)")
    tax_rate: Optional[Decimal] = Field(Decimal("0.00"), description="Applicable tax rate (e.g. 0.20 for 20%)")
    tax_amount: Optional[Decimal] = Field(Decimal("0.00"), description="Calculated tax for line")

    @field_validator("line_total", mode="after")
    @classmethod
    def verify_arithmetic(cls, v: Decimal, info) -> Decimal:
        qty = info.data.get("quantity")
        price = info.data.get("unit_price")
        if qty is not None and price is not None:
            expected = (qty * price).quantize(Decimal("0.01"))
            # Allow at most 0.02 rounding discrepancy
            if abs(v - expected) > Decimal("0.02"):
                raise ValueError(f"Line total {v} does not match qty {qty} * unit_price {price} = {expected}")
        return v

class CanonicalInvoice(BaseModel):
    invoice_number: str = Field(..., min_length=1, description="Vendor invoice number")
    vendor_name: str = Field(..., min_length=1, description="Legal vendor entity name")
    vendor_tax_id: Optional[str] = Field(None, description="Vendor VAT / Tax ID / EIN")
    invoice_date: date = Field(..., description="Date of invoice issuance")
    due_date: Optional[date] = Field(None, description="Payment due date")
    purchase_order_number: Optional[str] = Field(None, description="Referenced PO number (e.g. PO-2024-001)")
    currency: str = Field("USD", min_length=3, max_length=3, description="ISO 4217 currency code")
    subtotal: Decimal = Field(..., ge=0, description="Total amount before taxes")
    tax_total: Decimal = Field(Decimal("0.00"), ge=0, description="Total tax amount")
    grand_total: Decimal = Field(..., ge=0, description="Subtotal + tax_total")
    line_items: List[InvoiceLineItem] = Field(..., min_length=1, description="List of line items")

    # Metadata tracked by engine
    raw_document_hash: str = Field(..., description="SHA-256 hash of original file")
    extraction_provider: str = Field(..., description="Provider that performed extraction: 'gemini' or 'qwen'")
    extraction_confidence: Optional[Decimal] = Field(Decimal("1.00"), description="Provider confidence score [0.0-1.0]")
```

## 2. Invariants
1. All monetary fields MUST use `Decimal` with 2 decimal places (`0.01`).
2. `grand_total` must equal `subtotal + tax_total` within a 0.02 rounding tolerance.
3. If an extraction provider returns floats or missing fields, the parsing layer must coerce or reject before domain processing.
