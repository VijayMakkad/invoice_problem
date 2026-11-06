import logging
import time
from typing import Optional, List, Dict, Any
from decimal import Decimal
from src.domain.invoice import CanonicalInvoice
from src.extraction.providers.base import ExtractionResult
from src.extraction.providers.gemini_provider import GeminiExtractionProvider
from src.extraction.providers.qwen_provider import QwenOllamaExtractionProvider
from src.storage.repositories.audit_repository import AuditRepository
from src.exceptions.errors import ExtractionError, ProviderTimeoutError, ProviderQuotaExhaustedError, MalformedResponseError

logger = logging.getLogger(__name__)

class ProviderRouter:
    """
    Orchestration router between Primary Gemini API and Secondary Ollama Qwen2.5-VL fallback.
    Applies 15-second timeout, controlled retries, automated failover, and telemetry audit logging.
    """
    def __init__(
        self,
        gemini_provider: Optional[GeminiExtractionProvider] = None,
        qwen_provider: Optional[QwenOllamaExtractionProvider] = None,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.gemini = gemini_provider or GeminiExtractionProvider()
        self.qwen = qwen_provider or QwenOllamaExtractionProvider()
        self.audit_repo = audit_repo

    async def extract(
        self,
        document_bytes: bytes,
        mime_type: str,
        extracted_text: Optional[str] = None,
        page_images_b64: Optional[List[str]] = None,
        raw_document_hash: str = "",
    ) -> ExtractionResult:
        # Step 1: Attempt Primary Provider (Gemini)
        gemini_error = None
        try:
            result = await self.gemini.extract_invoice(
                document_bytes=document_bytes,
                mime_type=mime_type,
                extracted_text=extracted_text,
                page_images_b64=page_images_b64,
                raw_document_hash=raw_document_hash,
            )
            return result
        except (ProviderTimeoutError, ProviderQuotaExhaustedError, MalformedResponseError) as e:
            gemini_error = e
            logger.warning(f"Gemini primary extraction failed: {e}. Triggering fallback to local Qwen.")

        # Step 2: Log Fallback Telemetry Event
        if self.audit_repo:
            try:
                self.audit_repo.append_event(
                    entity_type="SYSTEM",
                    entity_id=raw_document_hash,
                    event_type="AI_PROVIDER_FALLBACK",
                    actor="ROUTER",
                    payload={
                        "primary": "gemini",
                        "secondary": "qwen2.5-vl",
                        "trigger_reason": str(gemini_error),
                        "timestamp": time.time(),
                    }
                )
            except Exception as audit_err:
                logger.error(f"Failed to record fallback audit event: {audit_err}")

        # Step 3: Attempt Secondary Fallback Provider (Ollama Qwen)
        try:
            result = await self.qwen.extract_invoice(
                document_bytes=document_bytes,
                mime_type=mime_type,
                extracted_text=extracted_text,
                page_images_b64=page_images_b64,
                raw_document_hash=raw_document_hash,
            )
            return result
        except Exception as qwen_err:
            logger.error(f"Qwen secondary fallback failed: {qwen_err}")
            raise ExtractionError(
                f"Both AI extraction providers failed: Primary (Gemini): {gemini_error}; Fallback (Qwen): {qwen_err}"
            )

