# InvoiceIQ Verification Workflow (Procedure C)

This workflow defines the end-to-end verification, regression testing, and acceptance certification process for InvoiceIQ.

## Steps

1. **Execute All Test Suites**:
   - Run unit tests, database integration tests, and scenario tests via `pytest`.
2. **Verify Acceptance Scenarios**:
   - Run H1 (Happy 2-Way), H2 (Happy 3-Way), H3 (Tolerance Match).
   - Run E1 (Overbilling), E2 (Cap Exceeded), E3 (Missing GRN), E4 (Duplicate), E5 (Unknown Vendor).
   - Assert all expected statuses and PO balance behaviors match `docs/fixture-manifest.md`.
3. **Verify Resilience & Fallback**:
   - Test Gemini-to-Qwen failover on simulated HTTP 429 and timeout.
   - Test revalidation on human edit.
4. **Conduct Technical & Security Review**:
   - Audit code with `invoiceiq-code-review` and `invoiceiq-security-review`.
5. **Issue Acceptance Report**:
   - Generate release readiness summary and test pass evidence.
