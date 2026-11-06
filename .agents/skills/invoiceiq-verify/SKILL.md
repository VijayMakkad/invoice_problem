---
name: invoiceiq-verify
description: >-
  Procedure C for InvoiceIQ: Comprehensive system verification, regression testing, acceptance validation, and
  pre-deployment auditing. Activate when verifying full system readiness, running end-to-end demonstrations
  (H1-H3, E1-E5), testing provider fallback, or preparing a release artifact.
---

# InvoiceIQ Verification Procedure (Procedure C)

This procedure governs the comprehensive end-to-end validation, regression testing, fixture evaluation, and security certification of the InvoiceIQ application before milestone sign-off or deployment.

## Prerequisites
- Feature implementation completed under Procedure B (`invoiceiq-implement`).
- All synthetic test fixtures available in `tests/fixtures/`.

## Execution Sequence

### Phase 1: Automated Test Suite Execution
Execute complete test suite across all layers:
```bash
# 1. Unit & Property Tests
pytest tests/unit/ -v

# 2. Database Integration & Transaction Tests
pytest tests/integration/ -v

# 3. Acceptance Scenarios
pytest tests/scenarios/ -v
```

### Phase 2: Golden Acceptance Fixture Evaluation
Run the eight core acceptance scenarios and verify status and allocation outcomes:
- [ ] **H1 (Happy 2-Way)**: Services invoice -> Status: `APPROVED`. PO balance consumed.
- [ ] **H2 (Happy 3-Way)**: Goods invoice matching GRN -> Status: `APPROVED`. PO balance consumed.
- [ ] **H3 (Tolerance Match)**: Variance within 2% -> Status: `APPROVED_WITH_TOLERANCE`. PO balance consumed.
- [ ] **E1 (Overbilling)**: Unit price > PO price -> Status: `BLOCKED`. PO balance intact.
- [ ] **E2 (PO Cap Exceeded)**: Billed qty > remaining -> Status: `BLOCKED`. PO balance intact.
- [ ] **E3 (Missing GRN)**: Physical goods with no GRN -> Status: `HOLD_FOR_REVIEW`. PO balance intact.
- [ ] **E4 (Duplicate Submission)**: Duplicate invoice number -> Status: `BLOCKED`. Unique constraint enforced.
- [ ] **E5 (Unknown Vendor)**: Unrecognized vendor entity -> Status: `BLOCKED`. Vendor registry check.

### Phase 3: Resilience & Provider Fallback Verification
1. Simulate Gemini API 429 quota exhaustion; assert automatic failover to local Qwen2.5-VL with audit event logging.
2. Simulate network latency > 15s; assert timeout catch and fallback.
3. Test human confirmation: modify line item on held invoice and verify complete revalidation execution.

### Phase 4: Independent Technical & Security Review
1. Invoke `invoiceiq-security-review`: verify zero hardcoded credentials and safe PDF parsing.
2. Invoke `invoiceiq-code-review`: generate formal review verdict against the four-tier taxonomy.

### Phase 5: Acceptance Certification Report
Compile and output the final **Acceptance & Readiness Report**:
- Full test pass/fail counts.
- Scenario outcome verification table.
- Residual risks or environment limitations.
- Sign-off recommendation for deployment.
