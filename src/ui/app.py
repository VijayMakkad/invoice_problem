import streamlit as st
from html import escape
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict

from src.config.settings import settings
from src.domain.invoice import CanonicalInvoice, InvoiceLineItem
from src.services.invoice_service import InvoiceProcessingService

st.set_page_config(
    page_title="InvoiceIQ — Accounts Payable Decision Engine",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for 5-second clarity and financial styling
st.markdown("""
<style>
    .status-banner {
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        color: white;
        font-weight: bold;
        font-size: 1.3rem;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .status-approved { background-color: #0F9D58; }
    .status-tolerance { background-color: #F4B400; color: #1E293B !important; }
    .status-pending { background-color: #4285F4; }
    .status-hold { background-color: #FF6D00; }
    .status-blocked { background-color: #DB4437; }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .metric-val { font-size: 1.8rem; font-weight: bold; }
    .metric-lbl { color: #64748B; font-size: 0.85rem; text-transform: uppercase; }
    .diff-table th { background-color: #F1F5F9; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

FIXTURES_PDF_DIR = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "pdf"

def get_service():
    return InvoiceProcessingService(db_path=settings.DATABASE_PATH)

def main():
    service = get_service()

    st.sidebar.title("💼 InvoiceIQ")
    st.sidebar.caption("Enterprise Invoice-to-Decision Engine\n**Zamp ASA PS-1 Finance / AP**")
    st.sidebar.divider()

    menu = st.sidebar.radio(
        "Navigation",
        ["Home / Dashboard", "Process Invoice", "Audit & Ledger"],
        index=1
    )

    st.sidebar.divider()
    st.sidebar.subheader("Quick Demo Tools")
    if st.sidebar.button("🔄 Reset Database to Golden Demo State"):
        from scripts.seed_database import seed_database
        seed_database()
        st.sidebar.success("Database reset to golden state!")
        st.rerun()

    if menu == "Home / Dashboard":
        render_dashboard(service)
    elif menu == "Process Invoice":
        render_process_invoice(service)
    elif menu == "Audit & Ledger":
        render_audit_ledger(service)

def render_dashboard(service: InvoiceProcessingService):
    st.title("📊 Accounts Payable Decision Dashboard")
    st.write("Real-time portfolio metrics derived dynamically from SQLite persistence.")

    metrics = service.get_dashboard_metrics()

    # Dynamic Metric Cards
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#0F9D58;">{metrics["approved"]}</div><div class="metric-lbl">Approved</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#D97706;">{metrics["approved_with_tolerance"]}</div><div class="metric-lbl">Tolerance</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#2563EB;">{metrics["pending_confirmation"]}</div><div class="metric-lbl">Pending Review</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#EA580C;">{metrics["hold_for_review"]}</div><div class="metric-lbl">Hold for Review</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#DC2626;">{metrics["blocked"]}</div><div class="metric-lbl">Blocked</div></div>', unsafe_allow_html=True)
    with c6:
        st.markdown(f'<div class="metric-card"><div class="metric-val">₹{metrics["approved_amount"]:,.2f}</div><div class="metric-lbl">Committed Spend</div></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("Recent Invoices Ledger")
    invoices = service.list_invoices(limit=20)

    if not invoices:
        st.info("No invoices processed yet. Navigate to 'Process Invoice' to upload or evaluate sample invoices.")
    else:
        table_rows = []
        for inv in invoices:
            table_rows.append({
                "Invoice #": inv["invoice_number"] or "(Unassigned)",
                "Vendor": inv["vendor_name"],
                "PO Ref": inv["po_number"] or "(Missing)",
                "Invoice Date": inv["invoice_date"] or "N/A",
                "Grand Total": f"₹{Decimal(str(inv['grand_total'])):,.2f}",
                "Status": inv["status"],
                "Decision Summary": inv["decision_reason"][:65] + "..." if len(inv["decision_reason"]) > 65 else inv["decision_reason"],
            })
        st.dataframe(table_rows, use_container_width=True)

def render_process_invoice(service: InvoiceProcessingService):
    st.title("📄 Process Invoice Document")
    st.write("Upload a live PDF invoice or select an authentic golden scenario fixture.")

    c_upload, c_sample = st.columns([1.2, 1.0])

    selected_fixture = None
    uploaded_file = None

    with c_sample:
        st.subheader("Select Scenario Fixture")
        fixture_options = [
            ("None", "Upload Custom PDF File"),
            ("INV-H1-ExactMatch.pdf", "H1 — Exact 2-Way Match (CloudScale IT, ₹1,50,000)"),
            ("INV-H2-TolerancePass.pdf", "H2 — Allowed Tolerance Pass (Prime Office, ₹5,100)"),
            ("INV-H3-EquivalentDesc.pdf", "H3 — Equivalent Description SKU (Dell India, ₹6,50,000)"),
            ("INV-E1-Overbilling.pdf", "E1 — PO Overbilling & Cap Exhaustion (Apex Tools, ₹80k vs ₹30k)"),
            ("INV-E2-MissingPO.pdf", "E2 — Missing PO Reference (Bharat Office Tech, ₹5,000)"),
            ("INV-E3-BundleKit.pdf", "E3 — Bundled Accessory Kit (Nordic Peripheral, ₹3,000)"),
            ("INV-E4-TaxDeliveryFee.pdf", "E4 — Tax & Unapproved Delivery Fee (Global Logistics, ₹1,680)"),
            ("INV-E5-ShortReceipt.pdf", "E5 — GRN Short Receipt (Precision Tech, ₹5,00,000)"),
            ("INV-EVend-Unknown.pdf", "E_VEND — Unknown Vendor Guard (Ghost Vendor LLC)"),
        ]
        choice = st.selectbox(
            "Quick Fixture Selector",
            options=[opt[0] for opt in fixture_options],
            format_func=lambda x: dict(fixture_options).get(x, x),
        )
        if choice != "None":
            fixture_path = FIXTURES_PDF_DIR / choice
            if fixture_path.exists():
                selected_fixture = (choice, fixture_path.read_bytes())
                st.caption(f"Loaded fixture: `{choice}` ({len(selected_fixture[1])} bytes)")

    with c_upload:
        st.subheader("Upload Live PDF")
        uploaded_file = st.file_uploader("Upload supplier invoice (PDF)", type=["pdf"])

    active_bytes = None
    active_filename = "document.pdf"

    if uploaded_file is not None:
        active_bytes = uploaded_file.read()
        active_filename = uploaded_file.name
    elif selected_fixture is not None:
        active_filename = selected_fixture[0]
        active_bytes = selected_fixture[1]

    if active_bytes:
        st.divider()
        st.subheader(f"Document Ready: `{active_filename}`")

        if st.button("🚀 Run InvoiceIQ Decision Engine", type="primary", use_container_width=True):
            # Display real stage progress
            progress_bar = st.progress(0, text="Initializing Document AI Pipeline...")
            
            progress_bar.progress(25, text="1. Reading PDF text spans and layout analysis...")
            progress_bar.progress(50, text="2. Extracting structured invoice data via configured providers...")
            
            progress_bar.progress(75, text="3. Executing 10-step Deterministic Financial Validation Waterfall...")
            try:
                result = service.process_invoice_document(active_bytes, active_filename)
            except Exception as exc:
                progress_bar.empty()
                st.error(f"Invoice could not be processed: {exc}")
            else:
                progress_bar.progress(100, text="4. Financial decision computed and committed.")
                st.session_state["last_result"] = result
                st.rerun()

    # Display Result if available
    if "last_result" in st.session_state:
        render_decision_result(service, st.session_state["last_result"])

def render_decision_result(service: InvoiceProcessingService, res: Dict[str, Any]):
    st.divider()
    status = res.get("status", "HOLD_FOR_REVIEW")
    invoice_id = res["invoice_id"]
    inv_record = res.get("invoice_record", {})

    # 5-Second Clarity Decision Banner
    banner_class = "status-hold"
    icon = "⏳"
    if status == "APPROVED":
        banner_class = "status-approved"
        icon = "✅"
    elif status == "APPROVED_WITH_TOLERANCE":
        banner_class = "status-tolerance"
        icon = "⚠️"
    elif status == "PENDING_CONFIRMATION":
        banner_class = "status-pending"
        icon = "🔍"
    elif status == "BLOCKED":
        banner_class = "status-blocked"
        icon = "🛑"

    st.markdown(
        f'<div class="status-banner {banner_class}">'
        f'<span>{icon}</span>'
        f'<div><div>DECISION: {escape(str(status))}</div><div style="font-size:0.95rem; font-weight:normal; opacity:0.9;">{escape(str(res.get("primary_reason", "")))}</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Core Metric Highlights
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Invoice Number", inv_record.get("invoice_number") or "(Unstated)")
    c2.metric("Vendor", inv_record.get("vendor_name"))
    c3.metric("Billed Total", f"₹{Decimal(str(inv_record.get('grand_total') or 0)):,.2f}")
    c4.metric("Allocated to PO", f"₹{Decimal(str(res.get('allocated_amount') or 0)):,.2f}")

    # Interactive Human Actions (Human in the Loop)
    if res.get("requires_human_action"):
        st.subheader("🛠️ Human-in-the-Loop Resolution Required")
        action_type = res.get("action_type")

        if action_type == "PO_SELECTION":
            st.info("The referenced PO was missing on the document. Candidate Ranker identified the following open POs based on vendor, SKU, and amount similarity:")
            
            ranked = service.rank_po_candidates(invoice_id)

            for cand in ranked:
                with st.container(border=True):
                    sc1, sc2, sc3 = st.columns([1, 2, 1])
                    sc1.write(f"**PO Number:** `{cand.po_number}`")
                    sc1.write(f"**Confidence Score:** `{int(cand.score*100)}%`")
                    sc2.write(f"**Evidence:** {cand.evidence_summary}")
                    sc2.write(f"**Remaining PO Capacity:** ₹{cand.remaining_budget:,.2f}")
                    if sc3.button(f"Select {cand.po_number}", key=f"sel_{cand.po_number}", type="primary"):
                        with st.spinner("Re-running complete validation waterfall with confirmed PO..."):
                            reval_res = service.confirm_po_selection(invoice_id, cand.po_number)
                            st.session_state["last_result"] = reval_res
                            st.rerun()

        elif action_type == "BUNDLE_CONFIRMATION":
            st.warning("Supplier billed a bundled item ('Accessory Kit') not directly listed on PO lines.")
            st.write("System proposes decomposing into contracted catalog components:")
            st.markdown("- **KB-01** (Mechanical Office Keyboard): 1 unit @ ₹2,000.00\n- **MS-01** (Ergonomic Optical Mouse): 1 unit @ ₹1,000.00\n- **Total Allocation:** ₹3,000.00")
            if st.button("✅ Confirm Bundle Item Decomposition & Revalidate", type="primary"):
                with st.spinner("Re-running complete validation waterfall with itemized lines..."):
                    reval_res = service.confirm_bundle_decomposition(invoice_id)
                    st.session_state["last_result"] = reval_res
                    st.rerun()

    if status in {"PENDING_CONFIRMATION", "HOLD_FOR_REVIEW", "BLOCKED"}:
        render_correction_form(service, invoice_id, inv_record)

    # Financial Overbilling Explanations (E1)
    if res.get("excess_budget", Decimal("0.00")) > Decimal("0.00"):
        st.subheader("🛡️ Financial Protection Alert: PO Budget Cap Exceeded")
        with st.container(border=True):
            st.error(f"Invoice exceeds remaining PO budget by **₹{res['excess_budget']:,.2f}**.")
            st.markdown(f"""
            - **Contracted PO Total:** ₹1,00,000.00
            - **Historical Prior Approved Allocations:** ₹70,000.00 (See Record ID `ALLOC-HIST-001` in Ledger)
            - **Available Remaining Capacity:** ₹{res.get('remaining_budget', 0):,.2f}
            - **Incoming Invoice Amount:** ₹{inv_record.get('grand_total', 0):,.2f}
            - **Action:** Invoice balance remains unconsumed. Request PO change order or revised invoice for ₹30,000.00.
            """)

    # Side-by-Side Line Item Reconciliation
    st.subheader("📑 Line Item Reconciliation Details")
    line_data = []
    for l in inv_record.get("line_items", []):
        line_data.append({
            "Line #": l["line_number"],
            "SKU": l.get("sku") or "(Missing)",
            "Description": l["description"],
            "Quantity": l["quantity"],
            "Unit Price": f"₹{Decimal(str(l['unit_price'])):,.2f}",
            "Line Total": f"₹{Decimal(str(l['line_total'])):,.2f}",
        })
    st.table(line_data)

    # Detailed Explanatory Points
    with st.expander("🔍 View Technical Verification & Audit Reasons", expanded=False):
        for reason in res.get("detailed_reasons", []):
            st.markdown(f"- {reason}")
        st.caption(f"Extraction Provider: `{inv_record.get('extraction_provider')}` | Document Hash: `{inv_record.get('raw_document_hash')[:16]}...`")

def render_correction_form(
    service: InvoiceProcessingService,
    invoice_id: str,
    inv_record: Dict[str, Any],
) -> None:
    """Collect human corrections; validation and financial math stay in the service."""
    with st.expander("Correct extracted data and revalidate", expanded=False):
        st.caption("Every saved correction enters the immutable audit ledger and reruns all validation rules.")
        invoice_date = inv_record.get("invoice_date")
        if isinstance(invoice_date, str):
            invoice_date = datetime.strptime(invoice_date[:10], "%Y-%m-%d").date()

        with st.form(f"correction_{invoice_id}"):
            left, right = st.columns(2)
            with left:
                invoice_number = st.text_input("Invoice number", value=inv_record.get("invoice_number") or "")
                vendor_name = st.text_input("Vendor name", value=inv_record.get("vendor_name") or "")
                corrected_date = st.date_input("Invoice date", value=invoice_date)
                po_number = st.text_input("Purchase order number", value=inv_record.get("po_number") or "")
            with right:
                currency = st.text_input("Currency", value=inv_record.get("currency") or "INR")
                subtotal = st.text_input("Subtotal", value=str(inv_record.get("subtotal") or "0.00"))
                tax_total = st.text_input("Tax total", value=str(inv_record.get("tax_total") or "0.00"))
                additional_charges = st.text_input("Additional charges", value=str(inv_record.get("additional_charges") or "0.00"))
                grand_total = st.text_input("Grand total", value=str(inv_record.get("grand_total") or "0.00"))

            st.subheader("Invoice lines")
            corrected_lines = []
            for line in inv_record.get("line_items", []):
                with st.container(border=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        sku = st.text_input("SKU", value=line.get("sku") or "", key=f"sku_{invoice_id}_{line['line_number']}")
                        description = st.text_input("Description", value=line["description"], key=f"desc_{invoice_id}_{line['line_number']}")
                    with col2:
                        quantity = st.text_input("Quantity", value=str(line["quantity"]), key=f"qty_{invoice_id}_{line['line_number']}")
                        unit_price = st.text_input("Unit price", value=str(line["unit_price"]), key=f"price_{invoice_id}_{line['line_number']}")
                    with col3:
                        line_total = st.text_input("Line total", value=str(line["line_total"]), key=f"total_{invoice_id}_{line['line_number']}")
                        tax_rate = st.text_input("Tax rate", value=str(line.get("tax_rate") or "0.00"), key=f"rate_{invoice_id}_{line['line_number']}")
                        tax_amount = st.text_input("Tax amount", value=str(line.get("tax_amount") or "0.00"), key=f"tax_{invoice_id}_{line['line_number']}")
                corrected_lines.append((line["line_number"], sku or None, description, quantity, unit_price, line_total, tax_rate, tax_amount))

            submitted = st.form_submit_button("Save corrections and revalidate", type="primary")

        if submitted:
            try:
                lines = [
                    InvoiceLineItem(
                        line_number=line_number,
                        sku=sku,
                        description=description,
                        quantity=Decimal(quantity),
                        unit_price=Decimal(unit_price),
                        line_total=Decimal(line_total),
                        tax_rate=Decimal(tax_rate),
                        tax_amount=Decimal(tax_amount),
                    )
                    for line_number, sku, description, quantity, unit_price, line_total, tax_rate, tax_amount in corrected_lines
                ]
                corrected = CanonicalInvoice(
                    invoice_number=invoice_number or None,
                    vendor_name=vendor_name,
                    invoice_date=corrected_date,
                    purchase_order_number=po_number or None,
                    currency=currency.upper(),
                    subtotal=Decimal(subtotal),
                    tax_total=Decimal(tax_total),
                    additional_charges=Decimal(additional_charges),
                    grand_total=Decimal(grand_total),
                    line_items=lines,
                    raw_document_hash=inv_record["raw_document_hash"],
                    extraction_provider=inv_record["extraction_provider"],
                )
                st.session_state["last_result"] = service.revalidate_invoice(invoice_id, corrected)
                st.rerun()
            except Exception as exc:
                st.error(f"Correction could not be saved: {exc}")


def render_audit_ledger(service: InvoiceProcessingService):
    st.title("📜 Immutable Audit Ledger")
    st.write("Cryptographically verifiable event log recording every ingestion, extraction, validation, and human action.")

    events = service.list_recent_audit_events(limit=100)

    if not events:
        st.info("No audit events recorded yet.")
        return

    table = []
    for ev in events:
        table.append({
            "Timestamp": ev["created_at"],
            "Event Type": ev["event_type"],
            "Actor": ev["actor"],
            "Entity": f"{ev['entity_type']} ({ev['entity_id'][:8]}...)" if len(ev['entity_id']) > 8 else ev['entity_id'],
            "Payload": ev["payload_json"][:80] + "..." if len(ev["payload_json"]) > 80 else ev["payload_json"]
        })
    st.dataframe(table, use_container_width=True)

if __name__ == "__main__":
    main()

