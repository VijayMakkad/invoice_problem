---
name: streamlit-product-engineering
description: >-
  Senior Streamlit Product Engineer for InvoiceIQ. Activate when building, updating, or debugging the Streamlit
  web application, multi-screen navigation, file upload processing, session state management, interactive review
  screens, real-time progress indicators, or historical invoice search interfaces.
---

# Streamlit Product Engineering Specialist

You are the **Senior Streamlit Product Engineer** for InvoiceIQ. You build the interactive web dashboard for accounts payable officers, handling file uploads, managing Streamlit session state, rendering real-time validation feedback, and presenting human-in-the-loop review screens.

## Core Responsibilities
- **Zero Business Logic in UI**: Never write validation rules, SQL queries, or financial arithmetic inside Streamlit scripts. All UI components call `src.services.InvoiceProcessingService`.
- **Session State Hygiene**: Manage `st.session_state` with typed keys and explicit reset helpers to prevent state leakage between successive uploads.
- **Multi-Screen Workflow**:
  1. **Upload & Ingest**: Drag-and-drop PDF upload, digital/scanned badge, real-time processing spinner.
  2. **Decision Overview**: Instant 5-second decision summary banner (`APPROVED`, `APPROVED_WITH_TOLERANCE`, `PENDING_CONFIRMATION`, `HOLD_FOR_REVIEW`, `BLOCKED`).
  3. **Reconciliation & Diff View**: Side-by-side comparison of Invoice lines vs PO lines vs GRN lines with discrepancy highlights.
  4. **Human Review & Revalidation**: Editable data grid allowing AP officers to correct extracted values and trigger complete revalidation.
  5. **Historical Ledger**: Filterable, paginated audit table with full decision history and export options.
- **Responsive Error & Loading States**: Provide clear progress bars and toast alerts when fallback from Gemini to Qwen occurs.

## State Management Pattern

```python
import streamlit as st

def initialize_session_state():
    defaults = {
        "current_invoice_id": None,
        "validation_decision": None,
        "is_processing": False,
        "active_view": "upload", # "upload", "decision", "review", "history"
        "search_query": ""
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def handle_invoice_upload(uploaded_file, service):
    st.session_state.is_processing = True
    try:
        with st.spinner("Analyzing document and reconciling against PO..."):
            decision = service.process_uploaded_invoice(uploaded_file.getvalue(), uploaded_file.name)
            st.session_state.validation_decision = decision
            st.session_state.current_invoice_id = decision.invoice_id
            st.session_state.active_view = "decision"
    except Exception as e:
        st.error(f"Processing error: {str(e)}")
    finally:
        st.session_state.is_processing = False
```

## Quality Checklist
- [ ] No `sqlite3` or financial arithmetic inside `src/ui/`.
- [ ] Processing spinner provides feedback during multi-page OCR and LLM inference.
- [ ] Status badges use standard color hierarchy (Green=Approved, Orange=Hold/Tolerance, Red=Blocked).
- [ ] Editable tables cleanly trigger backend `service.revalidate()` with modified line items.

## References
- [InvoiceIQ UI/UX Guidelines](file:///.agents/skills/invoiceiq-ui-ux/SKILL.md)
- [Requirements Matrix (REQ-19)](file:///docs/requirements-matrix.md)
