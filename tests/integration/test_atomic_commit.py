import pytest
import sqlite3
from decimal import Decimal
from src.storage.connection import get_connection
from src.storage.transaction import transaction
from src.storage.repositories.po_repository import PORepository
from src.storage.repositories.invoice_repository import InvoiceRepository

def test_atomic_transaction_rollback_on_failure(temp_db):
    conn = get_connection(temp_db)
    po_repo = PORepository(conn)
    inv_repo = InvoiceRepository(conn)

    # Initial PO state
    po_before = po_repo.get_by_number("PO-2024-001")
    initial_alloc = po_before.line_items[0].quantity_allocated

    # Attempt transaction where second step crashes
    with pytest.raises(RuntimeError, match="Simulated crash"):
        with transaction(conn):
            po_repo.increment_allocation("PO-2024-001", 1, Decimal("50.00"))
            # Force simulated unexpected failure
            raise RuntimeError("Simulated crash before invoice commit")

    # Verify atomic rollback
    po_after = po_repo.get_by_number("PO-2024-001")
    assert po_after.line_items[0].quantity_allocated == initial_alloc
    conn.close()

