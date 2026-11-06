import os
from pathlib import Path
from decimal import Decimal
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
EXCEL_DIR = FIXTURES_DIR / "excel"
PDF_DIR = FIXTURES_DIR / "pdf"

def generate_excel_workbooks():
    EXCEL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Purchase_Orders.xlsx
    wb_po = openpyxl.Workbook()
    # Sheet 1: Vendors
    ws_vendors = wb_po.active
    ws_vendors.title = "Vendors"
    ws_vendors.append(["vendor_id", "name", "tax_id", "status", "payment_terms"])
    vendors_data = [
        ["VEND-001", "CloudScale IT Solutions Pvt Ltd", "29ABCDE1234F1Z5", "ACTIVE", "NET30"],
        ["VEND-002", "Prime Office Supplies Ltd", "27FGHIJ5678K1Z2", "ACTIVE", "NET30"],
        ["VEND-003", "Dell Computer India Pvt Ltd", "29KLMNO9012P1Z8", "ACTIVE", "NET45"],
        ["VEND-004", "Apex Industrial Tools Corp", "27PQRST3456U1Z1", "ACTIVE", "NET30"],
        ["VEND-005", "Nordic Peripheral Systems", "29UVWXY7890A1Z4", "ACTIVE", "NET30"],
        ["VEND-006", "Global Logistics & Packaging", "27BCDEF2345G1Z9", "ACTIVE", "NET15"],
        ["VEND-007", "Precision Tech Systems Ltd", "29GHIJK6789L1Z3", "ACTIVE", "NET30"],
        ["VEND-008", "Bharat Office Tech Pvt Ltd", "27LMNOP0123Q1Z7", "ACTIVE", "NET30"],
    ]
    for row in vendors_data:
        ws_vendors.append(row)

    # Sheet 2: POs
    ws_pos = wb_po.create_sheet(title="POs")
    ws_pos.append(["po_number", "vendor_id", "issue_date", "matching_type", "currency", "total_amount", "status"])
    pos_data = [
        ["PO-2024-001", "VEND-001", "2024-10-01", "TWO_WAY", "INR", "150000.00", "ACTIVE"],
        ["PO-2024-002", "VEND-002", "2024-10-01", "THREE_WAY", "INR", "5000.00", "ACTIVE"],
        ["PO-2024-003", "VEND-003", "2024-10-01", "TWO_WAY", "INR", "650000.00", "ACTIVE"],
        ["PO-2024-004", "VEND-004", "2024-09-01", "TWO_WAY", "INR", "100000.00", "ACTIVE"],
        ["PO-2024-005", "VEND-005", "2024-10-05", "TWO_WAY", "INR", "30000.00", "ACTIVE"],
        ["PO-2024-006", "VEND-006", "2024-10-05", "TWO_WAY", "INR", "1000.00", "ACTIVE"],
        ["PO-2024-007", "VEND-007", "2024-10-05", "THREE_WAY", "INR", "500000.00", "ACTIVE"],
        ["PO-2024-008", "VEND-008", "2024-10-01", "TWO_WAY", "INR", "5000.00", "ACTIVE"],
        ["PO-2024-009", "VEND-008", "2024-10-10", "TWO_WAY", "INR", "10000.00", "ACTIVE"],
    ]
    for row in pos_data:
        ws_pos.append(row)

    # Sheet 3: PO_Items
    ws_po_items = wb_po.create_sheet(title="PO_Items")
    ws_po_items.append(["po_number", "line_number", "sku", "description", "quantity_ordered", "quantity_allocated", "unit_price", "tolerance_percent"])
    po_items_data = [
        ["PO-2024-001", 1, "SVC-DEV-01", "Cloud DevOps Consulting (Hours)", "100.00", "0.00", "1500.00", "0.02"],
        ["PO-2024-002", 1, "HW-OFF-01", "Ergonomic Executive Chair", "5.00", "0.00", "1000.00", "0.03"],
        ["PO-2024-003", 1, "DL-5440", "Dell Latitude 5440 Laptop", "10.00", "0.00", "65000.00", "0.02"],
        ["PO-2024-004", 1, "IND-TOOL-01", "Precision CNC Mill Cutters", "100.00", "70.00", "1000.00", "0.02"],
        ["PO-2024-005", 1, "KB-01", "Mechanical Office Keyboard", "10.00", "0.00", "2000.00", "0.02"],
        ["PO-2024-005", 2, "MS-01", "Ergonomic Optical Mouse", "10.00", "0.00", "1000.00", "0.02"],
        ["PO-2024-006", 1, "MAT-BOX-01", "Heavy Duty Packing Cartons", "1.00", "0.00", "1000.00", "0.02"],
        ["PO-2024-007", 1, "NB-PRO-15", "Enterprise Commercial Laptop", "10.00", "0.00", "50000.00", "0.02"],
        ["PO-2024-008", 1, "HW-DESK-01", "Modular Workstation Desk", "5.00", "0.00", "1000.00", "0.02"],
        ["PO-2024-009", 1, "HW-DESK-01", "Modular Workstation Desk", "10.00", "0.00", "1000.00", "0.02"],
    ]
    for row in po_items_data:
        ws_po_items.append(row)

    wb_po.save(EXCEL_DIR / "Purchase_Orders.xlsx")

    # 2. Goods_Receipts.xlsx
    wb_grn = openpyxl.Workbook()
    # Sheet 1: GRNs
    ws_grn = wb_grn.active
    ws_grn.title = "GRNs"
    ws_grn.append(["grn_number", "po_number", "vendor_name", "received_date", "received_by"])
    grns_data = [
        ["GRN-2024-002", "PO-2024-002", "Prime Office Supplies Ltd", "2024-10-15", "WH-Inspector-1"],
        ["GRN-2024-007", "PO-2024-007", "Precision Tech Systems Ltd", "2024-10-18", "WH-Inspector-2"],
    ]
    for row in grns_data:
        ws_grn.append(row)

    # Sheet 2: GRN_Items
    ws_grn_items = wb_grn.create_sheet(title="GRN_Items")
    ws_grn_items.append(["grn_number", "line_number", "po_line_number", "sku", "quantity_received", "quantity_invoiced", "receipt_condition"])
    grn_items_data = [
        ["GRN-2024-002", 1, 1, "HW-OFF-01", "5.00", "0.00", "GOOD"],
        ["GRN-2024-007", 1, 1, "NB-PRO-15", "7.00", "0.00", "GOOD"],
    ]
    for row in grn_items_data:
        ws_grn_items.append(row)

    wb_grn.save(EXCEL_DIR / "Goods_Receipts.xlsx")

def create_pdf(
    filename: Path,
    title: str,
    vendor_name: str,
    inv_num: str,
    inv_date: str,
    po_num: str,
    items: list,
    subtotal: str,
    tax: str,
    delivery_fee: str,
    grand_total: str
):
    doc = SimpleDocTemplate(str(filename), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    # Header
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1E3A8A'))
    story.append(Paragraph(f"TAX INVOICE — {vendor_name}", title_style))
    story.append(Spacer(1, 10))

    meta_text = f"""
    <b>Invoice Number:</b> {inv_num}<br/>
    <b>Date:</b> {inv_date}<br/>
    <b>Purchase Order Ref:</b> {po_num}<br/>
    <b>Currency:</b> INR (₹)<br/>
    """
    story.append(Paragraph(meta_text, styles['Normal']))
    story.append(Spacer(1, 15))

    # Table
    table_data = [["Line #", "SKU", "Description", "Qty", "Unit Price (₹)", "Line Total (₹)"]]
    for item in items:
        table_data.append([str(item[0]), str(item[1]), str(item[2]), str(item[3]), str(item[4]), str(item[5])])

    t = Table(table_data, colWidths=[40, 70, 200, 50, 80, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    # Summary
    summary_text = f"""
    <b>Subtotal:</b> ₹{subtotal}<br/>
    <b>GST (18%):</b> ₹{tax}<br/>
    <b>Delivery / Freight Fee:</b> ₹{delivery_fee}<br/>
    <b>Total Due:</b> ₹{grand_total}<br/>
    """
    story.append(Paragraph(summary_text, styles['Normal']))

    doc.build(story)

def generate_invoice_pdfs():
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    # H1 — Exact Two-Way Match
    create_pdf(
        PDF_DIR / "INV-H1-ExactMatch.pdf",
        "Cloud DevOps Consulting",
        "CloudScale IT Solutions Pvt Ltd",
        "INV-2024-H1-01",
        "2024-10-15",
        "PO-2024-001",
        [[1, "SVC-DEV-01", "Cloud DevOps Consulting (Hours)", "100.00", "1500.00", "150000.00"]],
        "150000.00", "0.00", "0.00", "150000.00"
    )

    # H2 — Allowed Tolerance Pass
    create_pdf(
        PDF_DIR / "INV-H2-TolerancePass.pdf",
        "Office Supplies",
        "Prime Office Supplies Ltd",
        "INV-2024-H2-02",
        "2024-10-16",
        "PO-2024-002",
        [[1, "HW-OFF-01", "Ergonomic Executive Chair", "5.00", "1020.00", "5100.00"]],
        "5100.00", "0.00", "0.00", "5100.00"
    )

    # H3 — Equivalent Description
    create_pdf(
        PDF_DIR / "INV-H3-EquivalentDesc.pdf",
        "Commercial Laptops",
        "Dell Computer India Pvt Ltd",
        "INV-2024-H3-03",
        "2024-10-16",
        "PO-2024-003",
        [[1, "DL-5440", "Dell Latitude 5440", "10.00", "65000.00", "650000.00"]],
        "650000.00", "0.00", "0.00", "650000.00"
    )

    # E1 — Overbilling & PO Budget Cap
    create_pdf(
        PDF_DIR / "INV-E1-Overbilling.pdf",
        "Industrial Cutters",
        "Apex Industrial Tools Corp",
        "INV-2024-E1-04",
        "2024-10-17",
        "PO-2024-004",
        [[1, "IND-TOOL-01", "Precision CNC Mill Cutters", "80.00", "1000.00", "80000.00"]],
        "80000.00", "0.00", "0.00", "80000.00"
    )

    # E2 — Missing PO Reference
    create_pdf(
        PDF_DIR / "INV-E2-MissingPO.pdf",
        "Modular Workstations",
        "Bharat Office Tech Pvt Ltd",
        "INV-2024-E2-05",
        "2024-10-17",
        "N/A",  # Missing PO
        [[1, "HW-DESK-01", "Modular Workstation Desk", "5.00", "1000.00", "5000.00"]],
        "5000.00", "0.00", "0.00", "5000.00"
    )

    # E3 — Bundled Accessory Kit
    create_pdf(
        PDF_DIR / "INV-E3-BundleKit.pdf",
        "Peripheral Kit",
        "Nordic Peripheral Systems",
        "INV-2024-E3-06",
        "2024-10-18",
        "PO-2024-005",
        [[1, "KIT-ACC-01", "Accessory Kit", "1.00", "3000.00", "3000.00"]],
        "3000.00", "0.00", "0.00", "3000.00"
    )

    # E4 — Tax and Extra Delivery Fee
    create_pdf(
        PDF_DIR / "INV-E4-TaxDeliveryFee.pdf",
        "Packing Cartons",
        "Global Logistics & Packaging",
        "INV-2024-E4-07",
        "2024-10-18",
        "PO-2024-006",
        [[1, "MAT-BOX-01", "Heavy Duty Packing Cartons", "1.00", "1000.00", "1000.00"]],
        "1000.00", "180.00", "500.00", "1680.00"
    )

    # E5 — GRN Short Receipt (10 units billed @ ₹50,000 = ₹5,00,000)
    create_pdf(
        PDF_DIR / "INV-E5-ShortReceipt.pdf",
        "Enterprise Laptops",
        "Precision Tech Systems Ltd",
        "INV-2024-E5-08",
        "2024-10-19",
        "PO-2024-007",
        [[1, "NB-PRO-15", "Enterprise Commercial Laptop", "10.00", "50000.00", "500000.00"]],
        "500000.00", "0.00", "0.00", "500000.00"
    )

    # E_VEND — Unknown Vendor
    create_pdf(
        PDF_DIR / "INV-EVend-Unknown.pdf",
        "Consulting Services",
        "Ghost Vendor LLC",
        "INV-2024-GHOST-99",
        "2024-10-20",
        "PO-2024-999",
        [[1, "UNREG-01", "Advisory Services", "1.00", "25000.00", "25000.00"]],
        "25000.00", "0.00", "0.00", "25000.00"
    )

if __name__ == "__main__":
    print("Generating Excel Master Workbooks...")
    generate_excel_workbooks()
    print("Generating Invoice PDFs...")
    generate_invoice_pdfs()
    print("All fixtures generated successfully!")

