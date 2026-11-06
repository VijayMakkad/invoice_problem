import sqlite3
from typing import Optional, List, Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from src.domain.purchase_order import PurchaseOrder, POLineItem
from src.domain.decision import MatchingType

class PORepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_by_number(self, po_number: str) -> Optional[PurchaseOrder]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM purchase_orders WHERE po_number = ?", (po_number,))
        po_row = cursor.fetchone()
        if not po_row:
            return None

        # Fetch lines
        cursor.execute("SELECT * FROM po_line_items WHERE po_number = ? ORDER BY line_number ASC", (po_number,))
        line_rows = cursor.fetchall()
        lines = [
            POLineItem(
                line_number=row["line_number"],
                sku=row["sku"],
                description=row["description"],
                quantity_ordered=Decimal(str(row["quantity_ordered"])),
                quantity_allocated=Decimal(str(row["quantity_allocated"])),
                unit_price=Decimal(str(row["unit_price"])),
                tolerance_percent=Decimal(str(row["tolerance_percent"])),
            )
            for row in line_rows
        ]

        # Fetch vendor name
        cursor.execute("SELECT name, tax_id FROM vendors WHERE vendor_id = ?", (po_row["vendor_id"],))
        v_row = cursor.fetchone()
        v_name = v_row["name"] if v_row else po_row["vendor_id"]
        v_tax = v_row["tax_id"] if v_row else None

        issue_dt = po_row["issue_date"]
        if isinstance(issue_dt, str):
            issue_date = datetime.strptime(issue_dt[:10], "%Y-%m-%d").date()
        else:
            issue_date = issue_dt

        return PurchaseOrder(
            po_number=po_row["po_number"],
            vendor_id=po_row["vendor_id"],
            vendor_name=v_name,
            vendor_tax_id=v_tax,
            issue_date=issue_date,
            matching_type=MatchingType(po_row["matching_type"]),
            currency=po_row["currency"],
            total_amount=Decimal(str(po_row["total_amount"])),
            status=po_row["status"],
            line_items=lines,
        )

    def find_by_vendor_id(self, vendor_id: str, status: str = "ACTIVE") -> List[PurchaseOrder]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT po_number FROM purchase_orders WHERE vendor_id = ? AND status = ?", (vendor_id, status))
        po_numbers = [row["po_number"] for row in cursor.fetchall()]
        return [self.get_by_number(num) for num in po_numbers if num is not None]

    def insert(self, po: PurchaseOrder) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO purchase_orders (po_number, vendor_id, issue_date, matching_type, currency, total_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(po_number) DO UPDATE SET
                vendor_id=excluded.vendor_id,
                issue_date=excluded.issue_date,
                matching_type=excluded.matching_type,
                currency=excluded.currency,
                total_amount=excluded.total_amount,
                status=excluded.status
            """,
            (
                po.po_number,
                po.vendor_id,
                po.issue_date.isoformat(),
                po.matching_type.value,
                po.currency,
                str(po.total_amount),
                po.status,
            )
        )
        for line in po.line_items:
            cursor.execute(
                """
                INSERT INTO po_line_items (po_number, line_number, sku, description, quantity_ordered, quantity_allocated, unit_price, tolerance_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(po_number, line_number) DO UPDATE SET
                    sku=excluded.sku,
                    description=excluded.description,
                    quantity_ordered=excluded.quantity_ordered,
                    quantity_allocated=excluded.quantity_allocated,
                    unit_price=excluded.unit_price,
                    tolerance_percent=excluded.tolerance_percent
                """,
                (
                    po.po_number,
                    line.line_number,
                    line.sku,
                    line.description,
                    str(line.quantity_ordered),
                    str(line.quantity_allocated),
                    str(line.unit_price),
                    str(line.tolerance_percent),
                )
            )

    def increment_allocation(self, po_number: str, line_number: int, qty_to_add: Decimal) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT quantity_allocated FROM po_line_items WHERE po_number = ? AND line_number = ?",
            (po_number, line_number)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"PO Line not found: {po_number} line {line_number}")
        current_qty = Decimal(str(row["quantity_allocated"]))
        new_qty = (current_qty + qty_to_add).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cursor.execute(
            "UPDATE po_line_items SET quantity_allocated = ? WHERE po_number = ? AND line_number = ?",
            (str(new_qty), po_number, line_number)
        )

