import pytest
import shutil
import tempfile
from pathlib import Path
from decimal import Decimal
from src.storage.connection import get_connection, init_db
from src.services.invoice_service import InvoiceProcessingService
from scripts.seed_database import seed_database
from scripts.generate_fixtures import generate_excel_workbooks, generate_invoice_pdfs

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures():
    """Ensure Excel workbooks and invoice PDFs exist."""
    generate_excel_workbooks()
    generate_invoice_pdfs()

@pytest.fixture
def temp_db():
    """Creates an isolated temporary SQLite database for test execution."""
    temp_dir = tempfile.mkdtemp()
    db_path = str(Path(temp_dir) / "test_invoiceiq.db")
    seed_database(db_path)
    yield db_path
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def service(temp_db):
    """Provides a fresh InvoiceProcessingService attached to temp_db."""
    return InvoiceProcessingService(db_path=temp_db)

@pytest.fixture
def pdf_fixtures():
    pdf_dir = FIXTURES_DIR / "pdf"
    return {p.name: p.read_bytes() for p in pdf_dir.glob("*.pdf")}

