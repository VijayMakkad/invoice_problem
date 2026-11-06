import sqlite3
import uuid
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from src.domain.invoice import CanonicalInvoice, InvoiceLineItem
from src.domain.decision import DecisionStatus

class InvoiceRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def find_by_hash(self, doc_hash: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE raw_document_hash = ? LIMIT 1", (doc_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def find_active_duplicate(self, vendor_id: Optional[str], invoice_number: Optional[str], exclude_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not vendor_id or not invoice_number:
            return None
        cursor = self.conn.cursor()
        query = """
            SELECT * FROM invoices 
            WHERE vendor_id = ? 
              AND invoice_number = ?
              AND status IN ('APPROVED', 'APPROVED_WITH_TOLERANCE', 'HOLD_FOR_REVIEW', 'PENDING_CONFIRMATION')
        """
        params = [vendor_id, invoice_number]
        if exclude_id:
            query += " AND invoice_id != ?"
            params.append(exclude_id)
        query += " LIMIT 1"
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def insert_invoice(
        self,
        invoice_id: str,
        invoice: CanonicalInvoice,
        status: DecisionStatus,
        decision_reason: str,
        vendor_id: Optional[str] = None,
        persist_po_number: Optional[str] = None,
    ) -> str:
        cursor = self.conn.cursor()
        inv_date_str = invoice.invoice_date.isoformat() if invoice.invoice_date else None
        
        cursor.execute(
            """
            INSERT INTO invoices (
                invoice_id, invoice_number, vendor_id, vendor_name, po_number,
                invoice_date, subtotal, tax_total, additional_charges, grand_total,
                currency, status, decision_reason, raw_document_hash, extraction_provider,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(invoice_id) DO UPDATE SET
                invoice_number=excluded.invoice_number,
                vendor_id=excluded.vendor_id,
                vendor_name=excluded.vendor_name,
                po_number=excluded.po_number,
                invoice_date=excluded.invoice_date,
                subtotal=excluded.subtotal,
                tax_total=excluded.tax_total,
                additional_charges=excluded.additional_charges,
                grand_total=excluded.grand_total,
                currency=excluded.currency,
                status=excluded.status,
                decision_reason=excluded.decision_reason,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                invoice_id,
                invoice.invoice_number,
                vendor_id,
                invoice.vendor_name,
                persist_po_number,
                inv_date_str,
                str(invoice.subtotal),
                str(invoice.tax_total),
                str(invoice.additional_charges),
                str(invoice.grand_total),
                invoice.currency,
                status.value,
                decision_reason,
                invoice.raw_document_hash,
                invoice.extraction_provider,
            )
        )

        # Clear and insert line items
        cursor.execute("DELETE FROM invoice_line_items WHERE invoice_id = ?", (invoice_id,))
        for line in invoice.line_items:
            cursor.execute(
                """
                INSERT INTO invoice_line_items (
                    invoice_id, line_number, sku, description, quantity, unit_price, line_total, tax_rate, tax_amount
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    line.line_number,
                    line.sku,
                    line.description,
                    str(line.quantity),
                    str(line.unit_price),
                    str(line.line_total),
                    str(line.tax_rate or Decimal("0.00")),
                    str(line.tax_amount or Decimal("0.00")),
                )
            )
        return invoice_id

    def record_allocation(
        self,
        po_number: str,
        po_line_number: int,
        invoice_id: str,
        invoice_line_number: int,
        quantity_allocated: Decimal,
        amount_allocated: Decimal
    ) -> str:
        alloc_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO po_allocations (
                allocation_id, po_number, po_line_number, invoice_id, invoice_line_number,
                quantity_allocated, amount_allocated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alloc_id,
                po_number,
                po_line_number,
                invoice_id,
                invoice_line_number,
                str(quantity_allocated),
                str(amount_allocated),
            )
        )
        return alloc_id

    def get_by_id(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,))
        inv_row = cursor.fetchone()
        if not inv_row:
            return None
        res = dict(inv_row)
        cursor.execute("SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY line_number ASC", (invoice_id,))
        res["line_items"] = [dict(r) for r in cursor.fetchall()]
        return res

    def list_invoices(
        self,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM invoices WHERE 1=1"
        params: List[Any] = []
        if status_filter and status_filter.upper() != "ALL":
            query += " AND status = ?"
            params.append(status_filter.upper())
        if search_query:
            query += " AND (LOWER(invoice_number) LIKE ? OR LOWER(vendor_name) LIKE ? OR LOWER(po_number) LIKE ?)"
            term = f"%{search_query.lower()}%"
            params.extend([term, term, term])
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT status, grand_total FROM invoices")
        rows = cursor.fetchall()
        counts = {
            "APPROVED": 0,
            "APPROVED_WITH_TOLERANCE": 0,
            "PENDING_CONFIRMATION": 0,
            "HOLD_FOR_REVIEW": 0,
            "BLOCKED": 0,
        }
        approved_amount = Decimal("0.00")
        for row in rows:
            status = row["status"]
            if status in counts:
                counts[status] += 1
            if status in ("APPROVED", "APPROVED_WITH_TOLERANCE"):
                approved_amount += Decimal(str(row["grand_total"]))
        return {
            "approved": counts["APPROVED"],
            "approved_with_tolerance": counts["APPROVED_WITH_TOLERANCE"],
            "pending_confirmation": counts["PENDING_CONFIRMATION"],
            "hold_for_review": counts["HOLD_FOR_REVIEW"],
            "blocked": counts["BLOCKED"],
            "total_invoices": len(rows),
            "approved_amount": approved_amount.quantize(Decimal("0.01")),
        }

