import sqlite3
from typing import Optional, Dict, Any

class VendorRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_by_id(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vendors WHERE vendor_id = ?", (vendor_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def find_by_name_or_tax_id(self, name: str, tax_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        if tax_id:
            cursor.execute("SELECT * FROM vendors WHERE tax_id = ?", (tax_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        
        # Fuzzy / lowercase match on vendor name
        cursor.execute("SELECT * FROM vendors WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))", (name,))
        row = cursor.fetchone()
        if row:
            return dict(row)

        # Fallback substring match
        cursor.execute("SELECT * FROM vendors WHERE LOWER(name) LIKE '%' || LOWER(?) || '%'", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def insert(self, vendor_id: str, name: str, tax_id: Optional[str], status: str = "ACTIVE", payment_terms: str = "NET30") -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO vendors (vendor_id, name, tax_id, status, payment_terms)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(vendor_id) DO UPDATE SET
                name=excluded.name,
                tax_id=excluded.tax_id,
                status=excluded.status,
                payment_terms=excluded.payment_terms
            """,
            (vendor_id, name, tax_id, status, payment_terms)
        )

