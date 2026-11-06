# InvoiceIQ — Gemini Context & Behavior Specification

This repository hosts **InvoiceIQ**, an intelligent accounts payable decision system for **Zamp ASA**.

## Primary Operating Principles
1. **Never Invent Business Rules**: Adhere strictly to the Zamp ASA PS-1 specification. When ambiguity arises, reference `docs/requirements-matrix.md` and `docs/architecture-contract.md`.
2. **Deterministic Financial Validation**: LLM extractions (Gemini 2.5/Flash or Qwen2.5-VL 3B) are strictly treated as candidate structured inputs. Approval, hold, or rejection statuses are computed exclusively via the Python deterministic rule engine (`financial-validation-engine`).
3. **Decimal Precision**: Never use IEEE 754 floating point numbers for currency, unit prices, tax amounts, or cumulative allocations. Always use Python `Decimal`.
4. **Three-Way Matching Invariance**: If a PO requires a Goods Received Note (GRN), the engine must never silently fall back to a two-way match. Missing GRNs trigger an explicit `HOLD FOR REVIEW` or `BLOCKED` status.
5. **Idempotency & Auditability**: Every invoice ingestion, extraction, validation, and confirmation must be permanently recorded with timestamps, user/actor identity, and immutable historical records in SQLite.

## Workspace Customizations
- Rules are located in `.agents/rules/`.
- Specialist skills are located in `.agents/skills/`.
- Reference architecture and documentation are located in `docs/`.
