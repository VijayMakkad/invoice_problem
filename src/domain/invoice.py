from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class InvoiceLineItem(BaseModel):
    line_number: int = Field(..., description="1-based item index on invoice")
    sku: Optional[str] = Field(None, description="Item SKU or code")
    description: str = Field(..., min_length=1, description="Item description")
    quantity: Decimal = Field(..., gt=0, description="Quantity billed")
    unit_price: Decimal = Field(..., ge=0, description="Price per unit")
    line_total: Decimal = Field(..., ge=0, description="Quantity * unit_price")
    tax_rate: Optional[Decimal] = Field(Decimal("0.00"), description="Tax rate, e.g. 0.18 for 18%")
    tax_amount: Optional[Decimal] = Field(Decimal("0.00"), description="Tax amount for line")

    @field_validator("line_total", mode="after")
    @classmethod
    def verify_arithmetic(cls, v: Decimal, info) -> Decimal:
        qty = info.data.get("quantity")
        price = info.data.get("unit_price")
        if qty is not None and price is not None:
            expected = (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if abs(v - expected) > Decimal("0.02"):
                raise ValueError(f"Line total {v} differs from quantity {qty} * unit_price {price} = {expected}")
        return v

class CanonicalInvoice(BaseModel):
    invoice_number: Optional[str] = Field(None, description="Vendor invoice number, or None if unstated/unreadable")
    vendor_name: str = Field(..., min_length=1, description="Vendor legal entity name")
    vendor_tax_id: Optional[str] = Field(None, description="Vendor GSTIN / VAT / Tax ID")
    invoice_date: Optional[date] = Field(None, description="Date of invoice issuance, or None if unstated/unreadable")
    due_date: Optional[date] = Field(None, description="Payment due date")
    purchase_order_number: Optional[str] = Field(None, description="Referenced PO number, e.g. PO-2024-001")
    currency: str = Field("INR", min_length=3, max_length=3, description="ISO 4217 currency code")
    subtotal: Decimal = Field(..., ge=0, description="Subtotal before taxes and fees")
    tax_total: Decimal = Field(Decimal("0.00"), ge=0, description="Total tax amount")
    additional_charges: Decimal = Field(Decimal("0.00"), ge=0, description="Freight, delivery, or extra charges")
    grand_total: Decimal = Field(..., ge=0, description="Subtotal + tax_total + additional_charges")
    line_items: List[InvoiceLineItem] = Field(..., min_length=1, description="List of line items")
    raw_document_hash: str = Field(..., description="SHA-256 hash of original file")
    extraction_provider: str = Field(..., description="'gemini' or 'qwen'")
    extraction_confidence: Decimal = Field(Decimal("1.00"), ge=0, le=1, description="Confidence score")

    @field_validator("grand_total", mode="after")
    @classmethod
    def verify_grand_total(cls, v: Decimal, info) -> Decimal:
        subtotal = info.data.get("subtotal") or Decimal("0.00")
        tax_total = info.data.get("tax_total") or Decimal("0.00")
        add_charges = info.data.get("additional_charges") or Decimal("0.00")
        expected = (subtotal + tax_total + add_charges).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if abs(v - expected) > Decimal("0.02"):
            raise ValueError(f"Grand total {v} does not equal subtotal {subtotal} + tax {tax_total} + fees {add_charges} = {expected}")
        return v

