# InvoiceIQ Implementation Workflow (Procedure B)

This workflow defines the disciplined, test-driven implementation sequence for InvoiceIQ features.

## Steps

1. **Review Approved Plan**:
   - Inspect plan artifact created during `invoiceiq-plan`.
2. **Execute Layered Build**:
   - Database & Storage: Activate `database-audit-engineering`.
   - Domain & Deterministic Engine: Activate `financial-validation-engine`.
   - Document & AI Extraction: Activate `invoice-document-intelligence` and `gemini-qwen-orchestration`.
   - Backend Services: Activate `python-backend-engineering`.
   - Presentation: Activate `streamlit-product-engineering` and `invoiceiq-ui-ux`.
3. **Execute Automated Tests**:
   - Run `pytest tests/ -v` via `invoiceiq-qa-testing`.
4. **Peer Review & Verification**:
   - Run security audit with `invoiceiq-security-review`.
   - Run code review with `invoiceiq-code-review`.
5. **Report Evidence**:
   - Output files modified, tests executed, and requirement criteria satisfied.
