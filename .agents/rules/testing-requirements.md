# Rule: Testing & Quality Verification Requirements

## 1. Test-Driven Verification Invariant
- No feature, bug fix, or refactor is considered complete without executing test evidence.
- Agents must never report a task as complete without citing pytest execution results, test names, and pass counts.

## 2. Test Pyramid & Scope
- **Unit Tests (`tests/unit/`)**:
  - Pure financial math tests (tax rounding, line sum calculation, price tolerance boundaries).
  - Pydantic schema validation tests (canonical invoice, PO, GRN).
  - Fallback logic tests using mocked LLM provider responses.
- **Integration Tests (`tests/integration/`)**:
  - SQLite database transactions, foreign key enforcement, atomic allocation locking, and audit log persistence.
  - End-to-end extraction pipeline with synthetic PDF inputs and mocked AI provider endpoints.
- **Scenario Tests (`tests/scenarios/`)**:
  - Full execution of standard test cases:
    - Happy paths: H1 (Exact match 2-way), H2 (Exact match 3-way with GRN), H3 (Match within acceptable tolerance).
    - Exception cases: E1 (Overbilling / unit price mismatch), E2 (Quantity exceeds PO cap), E3 (Missing GRN on 3-way match), E4 (Duplicate invoice submission), E5 (Unknown vendor / unapproved PO).

## 3. Provider Contract Testing
- Gemini and Qwen provider adapters must be tested against the canonical schema.
- Both providers must produce outputs that pass identical Pydantic schema validators.
- Test scenarios must explicitly verify automatic fallback from Gemini to Qwen upon timeout, quota exhaustion (HTTP 429), or malformed response.

## 4. Rerun & Idempotency Testing
- Submitting the same invoice file twice must trigger duplicate detection (or idempotent update if explicit revalidation is requested).
- Testing human confirmation must verify that modifying line items triggers a full rerun of the validation engine and correctly updates PO committed balances.
