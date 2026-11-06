# Rule: Python Engineering & Coding Standards

## 1. Type Safety and Annotations
- All production Python code must include complete type annotations (`from typing import Optional, List, Dict, Union, Any`, etc.).
- Function signatures must declare argument types and return types.
- Pydantic v2 models must be used for all internal domain transfer objects, API payloads, and configuration models.

## 2. Modularity & Clean Architecture
- Follow the Service-Repository pattern:
  - **Repositories**: Handle SQLite database queries, connections, and transactional boundary management.
  - **Services**: Contain business workflows, coordinate document processing, invoke AI providers, and orchestrate validation rules.
  - **Domain / Models**: Pure Pydantic definitions and domain entities containing no I/O or external dependencies.
- Keep functions small, single-purpose, and testable (< 40 lines preferred).
- Prohibit circular dependencies. Enforce one-way dependency flow: `UI -> Service -> Repository / Engine -> Core Models`.

## 3. Explicit Exception Handling
- Custom domain exceptions must inherit from a base `InvoiceIQError` (e.g., `ValidationError`, `POExhaustedError`, `ProviderExtractionError`, `ConcurrencyError`).
- Never catch generic `Exception` without re-raising or logging with structured traceback details.
- Never swallow errors silently or return `None` when a failure occurred.

## 4. Structured Logging & Observability
- Use standard Python `logging` configured with structured JSON formatters in production.
- Include contextual attributes in log records: `invoice_id`, `vendor_id`, `po_number`, `provider_used`, `duration_ms`.
- Do not log sensitive data (API keys, raw credentials, unredacted banking details).

## 5. Configuration & Secret Management
- All configuration settings (API keys, timeouts, database paths, tolerance thresholds) must be read from environment variables or `.env` files via `pydantic-settings`.
- No API keys, credentials, or GCP secrets may ever be hardcoded in source files.
- Default to secure local fallbacks when cloud secrets are unavailable.
