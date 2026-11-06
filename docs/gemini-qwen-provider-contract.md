# Gemini & Qwen Dual-Provider Orchestration Contract

This document defines the interface, schema enforcement, fallback routing, and error handling protocols for LLM invoice extraction.

## 1. Provider Topology

- **Primary Provider**: Google Gemini API (`gemini-2.5-flash` or current stable multimodal model) accessed via the official `google-genai` SDK or REST API.
- **Secondary Local Fallback Provider**: `Qwen2.5-VL 3B` running locally via Ollama (`http://localhost:11434/api/generate`).

```
                      [Invoice Document PDF/Image]
                                   │
                                   ▼
                       [Provider Router Facade]
                                   │
                 ┌─────────────────┴─────────────────┐
                 │ Try Primary                       │
                 ▼                                   ▼
        [Gemini API Call]                   (If Gemini Fails)
                 │                                   │
       ┌─────────┴─────────┐                         │ Fallback Trigger:
       │ Success           │ Failure                 │ - Timeout (>15s)
       ▼                   ▼                         │ - 429 Quota Exhausted
  [Validate JSON]   [Trigger Fallback] ──────────────┤ - 5xx Server Error
       │                   │                         │ - JSON Schema Error
       │                   ▼                         ▼
       │         [Ollama Qwen2.5-VL Call]   [Log Fallback Event]
       │                   │                         │
       │                   ▼                         │
       └─────────► [Validate JSON] ◄─────────────────┘
                           │
                           ▼
               [CanonicalInvoice Pydantic]
```

## 2. Common Extraction Prompt & Structured Schema
Both providers are invoked with the identical system prompt and JSON Schema definition.

```markdown
SYSTEM PROMPT:
You are an expert accounts payable document extraction system.
Extract all invoice metadata and line items from the provided document into valid JSON conforming exactly to the required schema.
Rules:
1. Never hallucinate or infer missing numbers.
2. Return all numbers as strings or decimals to preserve exact figures.
3. If an item code/SKU is present, extract it; otherwise set null.
4. If a Purchase Order number is mentioned anywhere on the document, extract it.
5. Return ONLY the raw JSON object. Do not wrap in markdown quotes.
```

## 3. Fallback Trigger Conditions
Fallback from Gemini to Qwen occurs automatically under any of the following circumstances:
1. **HTTP 429 (ResourceExhausted)**: Gemini API quota reached.
2. **Timeout**: Gemini network call exceeds `15.0 seconds`.
3. **HTTP 5xx (InternalServerError / ServiceUnavailable)**: Remote endpoint down.
4. **Validation Rejection**: Gemini response fails Pydantic schema validation after 1 retry.

## 4. Fallback Telemetry & Audit Requirement
Whenever fallback occurs, the system logs an audit entry to `audit_events`:
- `event_type`: `AI_PROVIDER_FALLBACK`
- `details`: `{"primary": "gemini", "secondary": "qwen2.5-vl", "reason": "<error_message>", "latency_ms": 15420}`
- The resulting invoice record maintains `extraction_provider = "qwen"`.
