---
name: invoiceiq-plan
description: >-
  Procedure A for InvoiceIQ: Requirements discovery, architectural design, and implementation planning. Activate
  when starting a new development cycle, reviewing the Zamp PS-1 specification, decomposing requirements, or
  producing an approved implementation plan before writing application code.
---

# InvoiceIQ Planning Procedure (Procedure A)

This procedure governs the initial requirements discovery, architectural boundary definition, risk assessment, and implementation planning phase for InvoiceIQ. It ensures that the engineering team aligns on specifications before any application code is authored.

## Prerequisites
- Knowledge of `docs/requirements-matrix.md` and `docs/architecture-contract.md`.
- No application implementation code may be written during this procedure.

## Execution Sequence

### Phase 1: Specification Ingestion & Inspection
1. **Read Core Documents**:
   - Inspect `docs/requirements-matrix.md` to map target user stories to REQ IDs.
   - Review `docs/financial-domain-glossary.md` and `docs/decision-statuses.md`.
2. **Inspect Existing Workspace**:
   - Verify existing repository layout, configuration files, and installed dependencies.

### Phase 2: Multi-Specialist Consultation
1. **Invoke `invoiceiq-architect`**:
   - Define system boundaries, module contracts, and interface abstractions.
2. **Invoke `accounts-payable-domain`**:
   - Clarify 2-way vs 3-way matching criteria, PO balance consumption rules, and GRN prerequisites.
3. **Invoke `invoice-document-intelligence` & `gemini-qwen-orchestration`**:
   - Determine ingestion strategy (PyMuPDF vs Tesseract OCR) and confirm canonical JSON schema constraints.
4. **Invoke `financial-validation-engine` & `database-audit-engineering`**:
   - Verify validation waterfall order and atomic transaction boundaries for PO balance commitments.

### Phase 3: Deliverable Generation
Produce an **Implementation Plan Artifact** containing:
- **Scope & Objectives**: Explicit REQ IDs covered.
- **Architecture Contract**: Service interfaces, Pydantic models, and database schema updates.
- **Risk & Mitigation Matrix**: Identified edge cases, fallback triggers, and quota considerations.
- **Acceptance Criteria**: List of specific pytest test files and fixtures to be implemented.

> [!IMPORTANT]
> **GATEWAY CHECKPOINT**: Stop and request explicit user confirmation on the Implementation Plan before proceeding to Procedure B (`invoiceiq-implement`).
