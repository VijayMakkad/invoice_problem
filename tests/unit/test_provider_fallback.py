import pytest
import asyncio
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from src.extraction.router import ProviderRouter
from src.extraction.providers.base import ExtractionResult
from src.domain.invoice import CanonicalInvoice, InvoiceLineItem
from src.exceptions.errors import ProviderQuotaExhaustedError, ProviderTimeoutError, ExtractionError

def create_sample_invoice(provider: str) -> CanonicalInvoice:
    return CanonicalInvoice(
        invoice_number="INV-FALLBACK-01",
        vendor_name="Test Vendor",
        invoice_date=date(2024, 10, 15),
        currency="INR",
        subtotal=Decimal("1000.00"),
        grand_total=Decimal("1000.00"),
        line_items=[
            InvoiceLineItem(
                line_number=1,
                sku="SKU-1",
                description="Test Line",
                quantity=Decimal("1.0"),
                unit_price=Decimal("1000.00"),
                line_total=Decimal("1000.00"),
            )
        ],
        raw_document_hash="test_hash",
        extraction_provider=provider,
    )

def test_provider_fallback_on_429():
    mock_gemini = AsyncMock()
    mock_gemini.extract_invoice.side_effect = ProviderQuotaExhaustedError("HTTP 429: Resource exhausted")

    mock_qwen = AsyncMock()
    qwen_inv = create_sample_invoice("qwen")
    mock_qwen.extract_invoice.return_value = ExtractionResult(
        invoice=qwen_inv,
        provider_name="qwen",
        latency_ms=250,
        raw_response_text="{}",
    )

    mock_audit = MagicMock()
    router = ProviderRouter(gemini_provider=mock_gemini, qwen_provider=mock_qwen, audit_repo=mock_audit)

    result = asyncio.run(router.extract(b"dummy_pdf", "application/pdf", raw_document_hash="hash_123"))

    assert result.provider_name == "qwen"
    assert result.invoice.extraction_provider == "qwen"
    # Verify fallback event was logged
    mock_audit.append_event.assert_called_once()
    call_args = mock_audit.append_event.call_args[1]
    assert call_args["event_type"] == "AI_PROVIDER_FALLBACK"
    assert "429" in call_args["payload"]["trigger_reason"]

def test_provider_fallback_on_timeout():
    mock_gemini = AsyncMock()
    mock_gemini.extract_invoice.side_effect = ProviderTimeoutError("Gemini call timed out after 15s")

    mock_qwen = AsyncMock()
    qwen_inv = create_sample_invoice("qwen")
    mock_qwen.extract_invoice.return_value = ExtractionResult(
        invoice=qwen_inv,
        provider_name="qwen",
        latency_ms=300,
        raw_response_text="{}",
    )

    mock_audit = MagicMock()
    router = ProviderRouter(gemini_provider=mock_gemini, qwen_provider=mock_qwen, audit_repo=mock_audit)

    result = asyncio.run(router.extract(b"dummy_pdf", "application/pdf", raw_document_hash="hash_456"))

    assert result.provider_name == "qwen"
    mock_audit.append_event.assert_called_once()
    assert mock_audit.append_event.call_args[1]["event_type"] == "AI_PROVIDER_FALLBACK"

def test_error_when_both_providers_fail():
    mock_gemini = AsyncMock()
    mock_gemini.extract_invoice.side_effect = ProviderTimeoutError("Gemini timeout")
    mock_qwen = AsyncMock()
    mock_qwen.extract_invoice.side_effect = Exception("Ollama connection refused")

    router = ProviderRouter(gemini_provider=mock_gemini, qwen_provider=mock_qwen)

    with pytest.raises(ExtractionError, match="Both AI extraction providers failed"):
        asyncio.run(router.extract(b"dummy_pdf", "application/pdf"))

