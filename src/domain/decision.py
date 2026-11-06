from enum import Enum
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field

class MatchingType(str, Enum):
    TWO_WAY = "TWO_WAY"
    THREE_WAY = "THREE_WAY"

class DecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    APPROVED_WITH_TOLERANCE = "APPROVED_WITH_TOLERANCE"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    HOLD_FOR_REVIEW = "HOLD_FOR_REVIEW"
    BLOCKED = "BLOCKED"

class LineDiscrepancy(BaseModel):
    line_number: int
    sku: Optional[str] = None
    issue_type: str  # e.g., "PRICE_TOLERANCE", "UNCONTRACTED_SKU", "SHORT_DELIVERY", "BUNDLE"
    message: str
    invoiced_value: Optional[str] = None
    contracted_value: Optional[str] = None
    variance_percent: Optional[Decimal] = None

class ValidationDecision(BaseModel):
    invoice_id: Optional[str] = None
    status: DecisionStatus
    primary_reason: str
    detailed_reasons: List[str] = Field(default_factory=list)
    line_discrepancies: List[LineDiscrepancy] = Field(default_factory=list)
    allocated_amount: Decimal = Field(default=Decimal("0.00"))
    excess_budget: Decimal = Field(default=Decimal("0.00"))
    remaining_budget: Decimal = Field(default=Decimal("0.00"))
    matched_sku: Optional[str] = None
    price_variance_percent: Optional[Decimal] = None
    is_replay: bool = False
    requires_human_action: bool = False
    action_type: Optional[str] = None  # "PO_SELECTION", "BUNDLE_CONFIRMATION", "FIELD_ENTRY"

