import sys
from pathlib import Path
from decimal import Decimal
import openpyxl

# Add repo root to python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.storage.connection import get_connection
from src.storage.repositories.vendor_repository import VendorRepository
from src.storage.repositories.po_repository import PORepository
from src.storage.repositories.grn_repository import GRNRepository
from src.domain.purchase_order import PurchaseOrder, POLineItem
from src.domain.goods_receipt import GoodsReceiptNote, GRNLineItem
from src.domain.decision import MatchingType
from datetime import datetime

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "excel"

def seed_database(db_path: str = settings.DATABASE_PATH):
    print(f"Seeding database at: {db_path}")
    conn = get_connection(db_path)
    vendor_repo = VendorRepository(conn)
    po_repo = PORepository(conn)
    grn_repo = GRNRepository(conn)

    # 1. Load Vendors & POs from Purchase_Orders.xlsx
    po_wb_path = FIXTURES_DIR / "Purchase_Orders.xlsx"
    if not po_wb_path.exists():
        raise FileNotFoundError(f"Missing {po_wb_path}. Run generate_fixtures.py first.")

    wb = openpyxl.load_workbook(po_wb_path)
    
    # Vendors
    ws_vendors = wb["Vendors"]
    vendor_names = {}
    for row in ws_vendors.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        v_id, name, tax_id, status, payment_terms = row
        vendor_names[str(v_id)] = str(name)
        vendor_repo.insert(v_id, name, tax_id, status or "ACTIVE", payment_terms or "NET30")

    # PO Items cache
    ws_po_items = wb["PO_Items"]
    po_lines_map = {}
    for row in ws_po_items.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        po_num, line_num, sku, desc, qty, alloc, price, tol = row
        if po_num not in po_lines_map:
            po_lines_map[po_num] = []
        po_lines_map[po_num].append(
            POLineItem(
                line_number=int(line_num),
                sku=str(sku),
                description=str(desc),
                quantity_ordered=Decimal(str(qty)),
                quantity_allocated=Decimal(str(alloc or "0.00")),
                unit_price=Decimal(str(price)),
                tolerance_percent=Decimal(str(tol or "0.02")),
            )
        )

    # POs
    ws_pos = wb["POs"]
    for row in ws_pos.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        po_num, v_id, dt, match_type, curr, total, status = row
        issue_date = datetime.strptime(str(dt)[:10], "%Y-%m-%d").date()
        po_obj = PurchaseOrder(
            po_number=str(po_num),
            vendor_id=str(v_id),
            vendor_name=vendor_names.get(str(v_id), f"Vendor {v_id}"),
            issue_date=issue_date,
            matching_type=MatchingType(str(match_type)),
            currency=str(curr or "INR"),
            total_amount=Decimal(str(total)),
            status=str(status or "ACTIVE"),
            line_items=po_lines_map.get(str(po_num), [])
        )
        po_repo.insert(po_obj)

    # 2. Load GRNs from Goods_Receipts.xlsx
    grn_wb_path = FIXTURES_DIR / "Goods_Receipts.xlsx"
    if grn_wb_path.exists():
        wb_grn = openpyxl.load_workbook(grn_wb_path)
        ws_grn_items = wb_grn["GRN_Items"]
        grn_lines_map = {}
        for row in ws_grn_items.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            grn_num, line_num, po_line_num, sku, rec_qty, inv_qty, cond = row
            if grn_num not in grn_lines_map:
                grn_lines_map[grn_num] = []
            grn_lines_map[grn_num].append(
                GRNLineItem(
                    line_number=int(line_num),
                    po_line_number=int(po_line_num),
                    sku=str(sku),
                    quantity_received=Decimal(str(rec_qty)),
                    quantity_invoiced=Decimal(str(inv_qty or "0.00")),
                    receipt_condition=str(cond or "GOOD"),
                )
            )

        ws_grns = wb_grn["GRNs"]
        for row in ws_grns.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            grn_num, po_num, v_name, dt, rec_by = row
            rec_date = datetime.strptime(str(dt)[:10], "%Y-%m-%d").date()
            grn_obj = GoodsReceiptNote(
                grn_number=str(grn_num),
                po_number=str(po_num),
                vendor_name=str(v_name),
                received_date=rec_date,
                received_by=str(rec_by),
                line_items=grn_lines_map.get(str(grn_num), [])
            )
            grn_repo.insert(grn_obj)

    # 3. Seed Prior Historical Invoice & Allocation for E1 (PO-2024-004: ₹70,000 allocated)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO invoices (
            invoice_id, invoice_number, vendor_id, vendor_name, po_number,
            invoice_date, subtotal, tax_total, additional_charges, grand_total,
            currency, status, decision_reason, raw_document_hash, extraction_provider
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(invoice_id) DO NOTHING
        """,
        (
            "INV-HIST-2024-01",
            "INV-2024-HIST-01",
            "VEND-004",
            "Apex Industrial Tools Corp",
            "PO-2024-004",
            "2024-09-15",
            "70000.00",
            "0.00",
            "0.00",
            "70000.00",
            "INR",
            "APPROVED",
            "Prior approved allocation for delivery batch 1",
            "historical_hash_batch_01",
            "manual_seed"
        )
    )
    cursor.execute(
        """
        INSERT INTO invoice_line_items (
            invoice_id, line_number, sku, description, quantity, unit_price, line_total, tax_amount
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(invoice_id, line_number) DO NOTHING
        """,
        (
            "INV-HIST-2024-01",
            1,
            "IND-TOOL-01",
            "Precision CNC Mill Cutters",
            "70.00",
            "1000.00",
            "70000.00",
            "0.00"
        )
    )
    cursor.execute(
        """
        INSERT INTO po_allocations (
            allocation_id, po_number, po_line_number, invoice_id, invoice_line_number,
            quantity_allocated, amount_allocated
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(allocation_id) DO NOTHING
        """,
        ("ALLOC-HIST-001", "PO-2024-004", 1, "INV-HIST-2024-01", 1, "70.00", "70000.00")
    )
    conn.commit()
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
