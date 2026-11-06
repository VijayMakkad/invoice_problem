---
name: invoiceiq-implement
description: >-
  Procedure B for InvoiceIQ: Feature development, test-driven implementation, and documentation. Activate after
  an implementation plan has been approved, when implementing domain models, services, AI extraction adapters,
  validation rules, UI components, or test fixtures.
---

# InvoiceIQ Implementation Procedure (Procedure B)

This procedure governs the disciplined, test-driven construction of InvoiceIQ features based on an approved plan from Procedure A (`invoiceiq-plan`).

## Prerequisites
- An approved implementation plan generated via `invoiceiq-plan`.
- Zero uncommitted conflicting changes in the workspace.

## Execution Sequence

### Phase 1: Context & Contract Setup
1. Review the approved implementation plan.
2. Ensure base Pydantic models in `src/domain/` conform to `docs/canonical-invoice-schema.md`.
3. If database models or repositories are touched, confirm SQLite DDL aligns with `docs/database-schema.md`.

### Phase 2: Feature Construction by Specialist Delegation
Execute implementation in dependency order:
1. **Domain & Storage Layer**:
   - Invoke `database-audit-engineering` to author repositories, DDL migrations, and atomic transaction blocks.
2. **Deterministic Financial Validation**:
   - Invoke `financial-validation-engine` to code business rules using Python `Decimal`.
3. **Document Ingestion & AI Extraction**:
   - Invoke `invoice-document-intelligence` to build PyMuPDF and Tesseract pipelines.
   - Invoke `gemini-qwen-orchestration` to implement provider adapters, router fallback, and telemetry.
4. **Application Services**:
   - Invoke `python-backend-engineering` to tie layers together into clean service facades.
5. **UI & Presentation**:
   - Invoke `streamlit-product-engineering` and `invoiceiq-ui-ux` to render workflows and decision screens.

### Phase 3: Immediate Verification & Test Execution
1. Author tests covering unit calculations, integration persistence, and edge scenarios.
2. Execute tests via `invoiceiq-qa-testing`:
   ```bash
   pytest tests/ -v
   ```
3. Run security checks via `invoiceiq-security-review`: verify no secrets leaked and input validation active.
4. Run peer review via `invoiceiq-code-review`: verify no critical blockers.

### Phase 4: Delivery Reporting
Report completion evidence including:
- Modified and created files.
- Pytest execution logs and pass counts.
- Traceability links to satisfaction of requirement IDs.
