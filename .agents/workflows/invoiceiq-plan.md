# InvoiceIQ Planning Workflow (Procedure A)

This workflow defines the systematic requirements intake, architectural design, and implementation planning procedure for InvoiceIQ.

## Steps

1. **Inspect Requirements**:
   - Read `docs/requirements-matrix.md` and `docs/architecture-contract.md`.
   - Identify relevant requirement IDs (REQ-01 through REQ-20).
2. **Consult Specialists**:
   - Activate `invoiceiq-architect` for system decomposition and module contracts.
   - Activate `accounts-payable-domain` for PO/GRN matching rules.
   - Activate `gemini-qwen-orchestration` and `invoice-document-intelligence` for extraction schemas.
   - Activate `financial-validation-engine` and `database-audit-engineering` for transaction boundaries.
3. **Produce Implementation Plan**:
   - Generate technical design, schema updates, risk mitigation, and test checklist.
4. **User Checkpoint**:
   - Present the plan to the user and await approval before implementing code.
