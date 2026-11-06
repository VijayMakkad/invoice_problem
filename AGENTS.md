# InvoiceIQ — Project Instruction and Governance Contract

This workspace contains **InvoiceIQ**, an enterprise automated invoice-to-decision system for **Zamp ASA (PS-1 Finance / AP)**.
Antigravity operates in this workspace as a coordinated team of 14 specialized engineering roles governed by persistent architectural and financial safety rules.

## Core Directives & Precedence

1. **Revised Specification is Sovereign**: The Zamp ASA PS-1 specification is the single source of truth. Do not invent business rules or assume relaxed constraints.
2. **Deterministic Financial Safety**: AI models (Gemini / Qwen) extract unstructured document data into canonical schemas; they **NEVER** decide invoice approvals. All financial rules, matching algorithms, tolerance checks, and decision statuses are strictly deterministic, auditable, and implemented in Python using `Decimal`.
3. **No Silent Mutations**: Original invoice files and raw extraction payloads are immutable. Corrected data generates an auditable correction event triggering complete revalidation.
4. **Strict Isolation of UI & Domain**: The Streamlit user interface must only invoke backend application services; UI code must contain zero business logic or validation math.
5. **Progressive Disclosure**: When working on specific features, invoke the specialist skills rather than attempting to hold the entire project in context.

## Active Project Rules
The following workspace rules are permanently enforced:
- [Core Architecture & Requirements Rules](file:///.agents/rules/invoiceiq-core.md)
- [Financial Safety & Decision Rules](file:///.agents/rules/financial-safety.md)
- [Coding Standards & Python Engineering](file:///.agents/rules/coding-standards.md)
- [Testing & Quality Verification Standards](file:///.agents/rules/testing-requirements.md)

## Specialist Skill Library
- [`invoiceiq-architect`](file:///.agents/skills/invoiceiq-architect/SKILL.md): Master orchestrator, boundaries, trade-offs, and requirement traceability.
- [`accounts-payable-domain`](file:///.agents/skills/accounts-payable-domain/SKILL.md): AP domain logic, PO lifecycles, 2-way/3-way matching, and allocations.
- [`invoice-document-intelligence`](file:///.agents/skills/invoice-document-intelligence/SKILL.md): PyMuPDF digital extraction, Tesseract OCR fallback, and multimodal coordinate grounding.
- [`gemini-qwen-orchestration`](file:///.agents/skills/gemini-qwen-orchestration/SKILL.md): Gemini API (primary) & Ollama Qwen2.5-VL 3B (fallback) provider contracts.
- [`financial-validation-engine`](file:///.agents/skills/financial-validation-engine/SKILL.md): High-precision `Decimal` arithmetic, tax, tolerance, duplicate detection, and decision statuses.
- [`database-audit-engineering`](file:///.agents/skills/database-audit-engineering/SKILL.md): SQLite transactional integrity, idempotency, foreign keys, and audit event logs.
- [`python-backend-engineering`](file:///.agents/skills/python-backend-engineering/SKILL.md): Modular service/repository architecture, Pydantic schemas, and typed contracts.
- [`streamlit-product-engineering`](file:///.agents/skills/streamlit-product-engineering/SKILL.md): Streamlit application state, multi-screen navigation, and review flows.
- [`invoiceiq-ui-ux`](file:///.agents/skills/invoiceiq-ui-ux/SKILL.md): AP officer ergonomics, 5-second clarity, decision badges, and exception drill-downs.
- [`invoiceiq-fixture-engineering`](file:///.agents/skills/invoiceiq-fixture-engineering/SKILL.md): Coherent test dataset generator (H1–H3, E1–E5, PO/GRN Excel files, synthetic PDFs).
- [`invoiceiq-qa-testing`](file:///.agents/skills/invoiceiq-qa-testing/SKILL.md): Comprehensive pytest suites, property tests, provider fallbacks, and acceptance matrix.
- [`gcp-cloudrun-devops`](file:///.agents/skills/gcp-cloudrun-devops/SKILL.md): Containerization, Cloud Run deployment, Secret Manager, and cloud billing isolation.
- [`invoiceiq-security-review`](file:///.agents/skills/invoiceiq-security-review/SKILL.md): Prompt injection defense, untrusted PDF sanitization, and secret protection.
- [`invoiceiq-code-review`](file:///.agents/skills/invoiceiq-code-review/SKILL.md): Independent gatekeeper, four-tier issue taxonomy, and specification compliance.

## Repeatable Execution Procedures
- [InvoiceIQ Planning Procedure](file:///.agents/skills/invoiceiq-plan/SKILL.md) (`/invoiceiq-plan`)
- [InvoiceIQ Implementation Procedure](file:///.agents/skills/invoiceiq-implement/SKILL.md) (`/invoiceiq-implement`)
- [InvoiceIQ Verification Procedure](file:///.agents/skills/invoiceiq-verify/SKILL.md) (`/invoiceiq-verify`)
