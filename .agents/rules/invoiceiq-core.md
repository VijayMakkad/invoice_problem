# Rule: InvoiceIQ Core Architecture & Operating Principles

## 1. Specification Sovereignty
- The revised Zamp ASA PS-1 specification is the definitive authority.
- No agent or engineer may invent, modify, or relax business rules, matching modes, tolerances, or decision criteria.
- All code, schemas, and test fixtures must maintain bidirectional traceability back to the requirements in `docs/requirements-matrix.md`.

## 2. Shared Single Engine Principle
- Test fixtures, demonstration invoices, and fresh live customer uploads must run through the exact same processing pipeline.
- Hardcoded demo shortcuts, bypassing validation for synthetic data, or mocking out the core engine in demo modes is strictly prohibited.

## 3. Modular Monolith Boundaries
- Code must reside within distinct service boundaries: Document Intelligence, AI Provider Orchestration, Financial Validation, and Storage/Audit.
- Circular dependencies between modules are forbidden.
- The UI layer (Streamlit) interacts with the system exclusively through public application service facades. Domain logic must never leak into Streamlit components.

## 4. Provider Interchangeability
- The extraction layer must abstract AI model providers behind a common interface (`InvoiceExtractionProvider`).
- Gemini API serves as the primary provider; local Qwen2.5-VL 3B via Ollama serves as the secondary fallback provider.
- Downstream processing modules must be completely agnostic to which provider performed the extraction.

## 5. Auditability and State Machine Governance
- Invoices transition through a formally defined state machine: `INGESTED` -> `EXTRACTED` -> `VALIDATING` -> `DECIDED` (`APPROVED`, `APPROVED_WITH_TOLERANCE`, `PENDING_CONFIRMATION`, `HOLD_FOR_REVIEW`, `BLOCKED`).
- Every state change, error, fallback event, and human action must generate an append-only audit log entry.
