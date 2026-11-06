# Requirements Matrix — Zamp ASA PS-1 Finance / InvoiceIQ

This document provides complete traceability between the Zamp ASA PS-1 Revised Specification and the InvoiceIQ software architecture.

## 1. System Objectives
InvoiceIQ is an enterprise Accounts Payable (AP) decision engine that takes invoice PDFs, extracts structured data using multimodal AI, matches line items against Purchase Orders (POs) and Goods Received Notes (GRNs), executes deterministic financial reconciliation, recommends actions, and tracks an auditable decision trail.

## 2. Requirement Traceability Matrix

| Req ID | Category | Requirement Description | Enforcing Component / Skill | Test Verification |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-01** | Ingestion | Accept PDF documents (digital and scanned) up to 20MB. | `invoice-document-intelligence` | `test_pdf_ingestion_formats` |
| **REQ-02** | OCR Fallback | Detect low-text PDFs and apply Tesseract OCR preprocessing. | `invoice-document-intelligence` | `test_scanned_pdf_ocr` |
| **REQ-03** | AI Extraction | Extract invoice header and line items into canonical JSON schema. | `gemini-qwen-orchestration` | `test_canonical_schema_compliance` |
| **REQ-04** | Dual Provider | Gemini API primary; Ollama local Qwen2.5-VL 3B secondary fallback. | `gemini-qwen-orchestration` | `test_provider_fallback_on_429` |
| **REQ-05** | Fallback Logging | Record provider choice, fallback trigger reason, latency, and tokens. | `gemini-qwen-orchestration` | `test_audit_fallback_telemetry` |
| **REQ-06** | PO Matching | Locate referenced PO; match vendor name/tax ID and line item SKUs. | `accounts-payable-domain` | `test_po_vendor_matching` |
| **REQ-07** | 2-Way Matching | For POs marked 2-way: match Invoice against PO quantity and unit price. | `financial-validation-engine` | `test_h1_two_way_match` |
| **REQ-08** | 3-Way Matching | For POs marked 3-way: match Invoice against PO price and GRN delivered quantity. | `financial-validation-engine` | `test_h2_three_way_match` |
| **REQ-09** | Tolerance Bounds | Allow configurable price variance (default ±2% on unit price / line total). | `financial-validation-engine` | `test_h3_tolerance_match` |
| **REQ-10** | Overbilling Check | Reject/hold when invoice price exceeds PO price beyond tolerance. | `financial-validation-engine` | `test_e1_overbilling_rejection` |
| **REQ-11** | PO Cap Exceeded | Block invoice if billed quantity exceeds remaining unallocated PO balance. | `financial-validation-engine` | `test_e2_po_cap_exhaustion` |
| **REQ-12** | Missing GRN | Hold invoice requiring 3-way match when no matching GRN exists. | `financial-validation-engine` | `test_e3_missing_grn_hold` |
| **REQ-13** | Duplicate Guard | Block invoice if invoice number + vendor ID already exists in DB. | `financial-validation-engine` | `test_e4_duplicate_invoice` |
| **REQ-14** | Unknown Vendor | Block invoice if vendor name or tax ID is not recognized in vendor registry. | `financial-validation-engine` | `test_e5_unknown_vendor` |
| **REQ-15** | State Invariants | Decisions: APPROVED, APPROVED_WITH_TOLERANCE, PENDING_CONFIRMATION, HOLD_FOR_REVIEW, BLOCKED. | `financial-validation-engine` | `test_decision_state_transitions` |
| **REQ-16** | Revalidation | Human correction triggers full revalidation, never raw status mutation. | `financial-validation-engine` | `test_human_override_revalidation` |
| **REQ-17** | Atomic Commitment| PO balance consumption and status approval committed in single SQLite transaction. | `database-audit-engineering` | `test_atomic_approval_transaction` |
| **REQ-18** | Immutable History | Original files and extraction data immutable; user edits stored as audit deltas. | `database-audit-engineering` | `test_audit_log_immutability` |
| **REQ-19** | AP UI | Streamlit dashboard: upload, 5-second decision clarity, review, search history. | `streamlit-product-engineering` | `test_ui_workflow_smoke` |
| **REQ-20** | Deployment | Dockerized container ready for GCP Cloud Run with Secret Manager integration. | `gcp-cloudrun-devops` | `test_container_build` |

## 3. Scenario Matrix
- **H1 (Happy 2-Way)**: Standard services invoice matching PO #PO-2024-001 within exact figures -> `APPROVED`.
- **H2 (Happy 3-Way)**: Physical goods invoice matching PO #PO-2024-002 and GRN #GRN-2024-002 exactly -> `APPROVED`.
- **H3 (Tolerance)**: Materials invoice with +1.5% freight/unit variance within 2% threshold -> `APPROVED_WITH_TOLERANCE`.
- **E1 (Overbilling)**: Unit price billed at \$125 vs PO price \$100 (25% variance) -> `BLOCKED` (Reason: Unit price exceeds PO).
- **E2 (Quantity Exceeded)**: Invoicing 120 units when remaining PO capacity is 50 -> `BLOCKED` (Reason: PO quantity cap exceeded).
- **E3 (Missing GRN)**: Physical goods delivery invoice submitted prior to warehouse receiving receipt -> `HOLD_FOR_REVIEW` (Reason: Pending GRN).
- **E4 (Duplicate Invoice)**: Submitting identical invoice number from existing active vendor -> `BLOCKED` (Reason: Duplicate invoice ID).
- **E5 (Unknown Vendor)**: Invoice from unvetted or unrecognized vendor entity -> `BLOCKED` (Reason: Unregistered vendor).
