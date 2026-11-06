import json
import time
import httpx
from typing import Optional, List, Dict, Any
from decimal import Decimal
from src.config.settings import settings
from src.domain.invoice import CanonicalInvoice
from src.extraction.providers.base import ExtractionResult
from src.extraction.providers.gemini_provider import EXTRACTION_SYSTEM_PROMPT
from src.exceptions.errors import ProviderTimeoutError, MalformedResponseError

class QwenOllamaExtractionProvider:
    """
    Local Secondary Fallback AI Provider: Qwen2.5-VL 3B running via Ollama.
    Communicates via Ollama REST API: http://localhost:11434/api/generate
    Produces identical CanonicalInvoice schema.
    """
    def __init__(self, base_url: Optional[str] = None, model_name: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model_name = model_name or settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS

    async def extract_invoice(
        self,
        document_bytes: bytes,
        mime_type: str,
        extracted_text: Optional[str] = None,
        page_images_b64: Optional[List[str]] = None,
        raw_document_hash: str = "",
    ) -> ExtractionResult:
        start_time = time.time()
        endpoint = f"{self.base_url.rstrip('/')}/api/generate"

        prompt = f"{EXTRACTION_SYSTEM_PROMPT}\n\nDocument Text Content:\n{extracted_text or 'No raw text available'}\n"

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        }

        if page_images_b64:
            payload["images"] = page_images_b64[:2]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code != 200:
                    raise MalformedResponseError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
                data = resp.json()
                raw_text = data.get("response", "{}")
        except httpx.TimeoutException:
            latency = int((time.time() - start_time) * 1000)
            raise ProviderTimeoutError(f"Ollama Qwen call timed out after {self.timeout}s (latency: {latency}ms).")
        except Exception as e:
            raise MalformedResponseError(f"Ollama extraction request failed: {e}")

        latency_ms = int((time.time() - start_time) * 1000)
        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")

        try:
            parsed_json = json.loads(raw_text)
            parsed_json["raw_document_hash"] = raw_document_hash
            parsed_json["extraction_provider"] = "qwen"
            parsed_json["extraction_confidence"] = Decimal("0.90")
            invoice = CanonicalInvoice(**parsed_json)
        except Exception as e:
            raise MalformedResponseError(f"Qwen response failed canonical validation: {e}")

        return ExtractionResult(
            invoice=invoice,
            provider_name="qwen",
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response_text=raw_text,
        )

