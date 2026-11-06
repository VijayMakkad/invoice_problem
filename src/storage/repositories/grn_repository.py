import sqlite3
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from src.domain.goods_receipt import GoodsReceiptNote, GRNLineItem

class GRNRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_by_po_number(self, po_number: str) -> Optional[GoodsReceiptNote]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM goods_receipt_notes WHERE po_number = ? ORDER BY received_date DESC LIMIT 1", (po_number,))
        grn_row = cursor.fetchone()
        if not grn_row:
            return None

        cursor.execute("SELECT * FROM grn_line_items WHERE grn_number = ? ORDER BY line_number ASC", (grn_row["grn_number"],))
        line_rows = cursor.fetchall()
        lines = [
            GRNLineItem(
                line_number=row["line_number"],
                po_line_number=row["po_line_number"],
                sku=row["sku"],
                quantity_received=Decimal(str(row["quantity_received"])),
                quantity_invoiced=Decimal(str(row["quantity_invoiced"])),
                receipt_condition=row["receipt_condition"],
            )
            for row in line_rows
        ]

        rec_dt = grn_row["received_date"]
        if isinstance(rec_dt, str):
            received_date = datetime.strptime(rec_dt[:10], "%Y-%m-%d").date()
        else:
            received_date = rec_dt

        return GoodsReceiptNote(
            grn_number=grn_row["grn_number"],
            po_number=grn_row["po_number"],
            vendor_name=grn_row["vendor_name"],
            received_date=received_date,
            received_by=grn_row["received_by"],
            line_items=lines,
        )

    def insert(self, grn: GoodsReceiptNote) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO goods_receipt_notes (grn_number, po_number, vendor_name, received_date, received_by)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(grn_number) DO UPDATE SET
                po_number=excluded.po_number,
                vendor_name=excluded.vendor_name,
                received_date=excluded.received_date,
                received_by=excluded.received_by
            """,
            (
                grn.grn_number,
                grn.po_number,
                grn.vendor_name,
                grn.received_date.isoformat(),
                grn.received_by,
            )
        )
        for line in grn.line_items:
            cursor.execute(
                """
                INSERT INTO grn_line_items (grn_number, line_number, po_line_number, sku, quantity_received, quantity_invoiced, receipt_condition)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(grn_number, line_number) DO UPDATE SET
                    po_line_number=excluded.po_line_number,
                    sku=excluded.sku,
                    quantity_received=excluded.quantity_received,
                    quantity_invoiced=excluded.quantity_invoiced,
                    receipt_condition=excluded.receipt_condition
                """,
                (
                    grn.grn_number,
                    line.line_number,
                    line.po_line_number,
                    line.sku,
                    str(line.quantity_received),
                    str(line.quantity_invoiced),
                    line.receipt_condition,
                )
            )

