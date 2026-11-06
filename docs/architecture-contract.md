# Architecture Contract & System Boundaries

## 1. System Topology: Modular Monolith
InvoiceIQ is designed as a clean, modular monolith in Python. It avoids the latency, operational overhead, and distributed transaction complexity of microservices, while enforcing strict module decoupling via Python abstract interfaces and Pydantic schemas.

```
                    ┌──────────────────────────────────────────────┐
                    │               Streamlit UI                   │
                    │   (Presentation / Workflows / Dashboards)    │
                    └──────────────────────┬───────────────────────┘
                                           │ invokes
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │         InvoiceIQ Application Service        │
                    │           (Orchestration Facade)            │
                    └──────┬───────────────┬───────────────┬───────┘
                           │               │               │
        ┌──────────────────┴──┐     ┌──────┴──────┐    ┌───┴─────────────────┐
        ▼                     ▼     ▼             ▼    ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌────────────────┐     ┌─────────────────┐
│  Document AI  │     │  LLM Provider │     │   Financial    │     │   Repository    │
│  Extraction   │     │ Orchestration │     │   Validation   │     │  & Audit Engine │
│ (PyMuPDF/OCR) │     │ (Gemini/Qwen) │     │  Rule Engine   │     │ (SQLite/Trans.) │
└───────────────┘     └───────────────┘     └────────────────┘     └─────────────────┘
```

## 2. Layer Definitions & Contracts

### A. Presentation Layer (`src/ui/`)
- Technology: Streamlit (`streamlit >= 1.35.0`).
- Responsibilities: File upload widgets, session state management, decision badge display, diff visualization for human overrides, searchable historical invoice ledger.
- Strict Invariant: Zero business logic. Must never perform arithmetic or modify status strings directly.

### B. Application Service Layer (`src/services/`)
- Coordinates the document pipeline:
  1. Calls Document Processing service to inspect PDF and produce normalized text / images.
  2. Passes payloads to AI Orchestration service to retrieve a `CanonicalInvoice`.
  3. Queries Repository for relevant PO, vendor, prior allocations, and GRN.
  4. Passes all domain objects into the Financial Validation Engine.
  5. If validation passes, opens an atomic database transaction to persist the invoice, write PO allocations, and append an audit event.

### C. Extraction & Provider Layer (`src/extraction/`)
- Defines `InvoiceExtractionProvider` protocol:
  ```python
  class InvoiceExtractionProvider(Protocol):
      async def extract_invoice(self, document_bytes: bytes, mime_type: str) -> ExtractionResult: ...
  ```
- Implementations:
  - `GeminiExtractionProvider`: Primary provider via Google GenAI SDK.
  - `QwenOllamaExtractionProvider`: Local secondary provider via Ollama API (`qwen2.5-vl:3b`).
  - `ProviderRouter`: Handles retries, timeout management (default 15s), and automatic fallback routing.

### D. Financial Validation Engine (`src/engine/`)
- Pure Python domain service with zero network I/O.
- Inputs: `CanonicalInvoice`, `PurchaseOrder`, optional `GoodsReceiptNote`, `List[HistoricalAllocation]`.
- Output: `ValidationDecision` object with status, line-by-line match results, tolerance calculations, blocking reasons, and recommended action.

### E. Persistence & Repository Layer (`src/storage/`)
- SQLite with WAL mode (`PRAGMA journal_mode=WAL;`).
- Foreign keys enabled (`PRAGMA foreign_keys=ON;`).
- Atomic commits for invoice state transitions and PO balance deductions.
- Immutable event log for auditing all actions (`audit_events` table).

## 3. Dependency Inversion Rules
1. High-level modules must not depend on low-level modules; both depend on abstractions.
2. Domain entities have zero third-party dependencies except Pydantic and standard library modules (`decimal`, `datetime`, `uuid`).
3. External adapters (Gemini, Ollama, Tesseract, SQLite) implement domain interfaces and can be mocked easily in pytest suites.
