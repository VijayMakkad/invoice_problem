from typing import Protocol, Dict, Any, List, Optional
from decimal import Decimal
from pydantic import BaseModel
from src.domain.invoice import CanonicalInvoice

class ExtractionResult(BaseModel):
    invoice: CanonicalInvoice
    provider_name: str
    latency_ms: int
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    raw_response_text: str

class InvoiceExtractionProvider(Protocol):
    """Protocol interface for AI invoice extraction providers."""
    async def extract_invoice(
        self,
        document_bytes: bytes,
        mime_type: str,
        extracted_text: Optional[str] = None,
        page_images_b64: Optional[List[str]] = None,
    ) -> ExtractionResult:
        ...

