# InvoiceIQ

InvoiceIQ is an accounts-payable invoice-to-decision engine for the Zamp ASA PS-1 Finance/AP workflow. It accepts invoice PDFs, extracts structured data, matches invoices against purchase orders and goods receipts, and produces an auditable deterministic decision.

The application is a Python modular monolith with a Streamlit interface and SQLite persistence.

## What it does

- Accepts digital and scanned PDF invoices up to 20 MB.
- Uses PyMuPDF for document parsing and Tesseract/OpenCV-based OCR fallback.
- Extracts invoice data through a provider abstraction:
  - Gemini is the primary provider.
  - Ollama Qwen2.5-VL 3B is the local fallback.
- Matches vendors, purchase orders, line items, quantities, prices, and goods receipts.
- Performs all financial arithmetic with `decimal.Decimal`.
- Applies deterministic two-way and three-way matching rules and configured price tolerances.
- Records immutable source documents, extraction payloads, decisions, allocations, and audit events in SQLite.
- Provides dashboard, invoice processing, review, and audit-ledger screens in Streamlit.

> **Financial safety:** AI providers only extract candidate structured data. They never approve invoices. Final statuses are computed by the deterministic validation engine.

## Decision statuses

| Status | Meaning |
| --- | --- |
| `APPROVED` | Exact match and all hard checks passed. |
| `APPROVED_WITH_TOLERANCE` | A permitted price variance was detected. |
| `PENDING_CONFIRMATION` | Human input is required, such as PO selection or bundle confirmation. |
| `HOLD_FOR_REVIEW` | A dependency or reviewable discrepancy remains, such as a missing/short GRN. |
| `BLOCKED` | A hard policy violation was detected, such as an unknown vendor or duplicate invoice. |

Approved invoices consume PO allocation only inside the same atomic SQLite transaction as the status change. Held, blocked, and pending invoices do not consume PO balances.

## Architecture

```text
Streamlit UI
    |
    v
InvoiceProcessingService
    |
    +-- DocumentParser              (PDF text, layout, OCR)
    +-- ProviderRouter              (Gemini -> Qwen fallback)
    +-- DeterministicValidationEngine
    +-- SQLite repositories         (vendors, POs, GRNs, invoices, audit)
```

Relevant source areas:

```text
src/
  config/       Environment-backed settings
  domain/       Pydantic domain models
  engine/       Matching, candidate ranking, validation, and decisions
  extraction/   PDF parsing and AI provider adapters
  services/     Application service facades
  storage/      SQLite connection, transactions, repositories, and audit
  ui/           Streamlit application
tests/
  unit/         Schemas, arithmetic, ranking, and provider fallback
  integration/  Database transactions and revalidation
  scenarios/    Happy paths and exception workflows
docs/           Architecture, requirements, schemas, and deployment guides
```

## Requirements

- Python 3.11+
- Tesseract OCR for scanned-document fallback
- Ollama with `qwen2.5vl:3b` only when local fallback extraction is needed
- A Gemini API key when using the primary cloud provider

## Local setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env` if Gemini extraction is enabled. Keep `.env` local and never commit credentials.

Generate the synthetic Excel/PDF fixtures and seed the local SQLite database:

```bash
python scripts/generate_fixtures.py
python scripts/seed_database.py
```

Start the application:

```bash
streamlit run src/ui/app.py
```

Then open the URL printed by Streamlit, normally `http://localhost:8501`.

The sidebar includes a **Reset Database to Golden Demo State** action. Sample invoices are available under `tests/fixtures/pdf/`.

## Configuration

Configuration is loaded from environment variables or `.env` through `src/config/settings.py`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_PATH` | `data/invoiceiq.db` | SQLite database location |
| `GEMINI_API_KEY` | empty | Gemini API credential |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Primary extraction model |
| `GEMINI_TIMEOUT_SECONDS` | `15.0` | Gemini timeout |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen2.5vl:3b` | Fallback extraction model |
| `OLLAMA_TIMEOUT_SECONDS` | `30.0` | Ollama timeout |
| `DEFAULT_TOLERANCE_PERCENT` | `0.02` | Default price tolerance |
| `ENABLE_GCS_BACKUP` | `false` | Enable experimental GCS backup |
| `GCS_BUCKET_NAME` | empty | GCS backup bucket |

See [.env.example](/Users/vijay/invoice_problem/.env.example) for the complete template.

## Testing

Run the complete test suite:

```bash
pytest tests/ -v
```

Run focused suites:

```bash
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/scenarios/ -v
```

The scenario suite covers exact two-way matching, three-way matching, tolerance handling, overbilling, PO capacity, missing/short receipts, additional charges, duplicate submissions, unknown vendors, PO selection, and human revalidation.

## Docker and Cloud Run

Build and run the container locally:

```bash
docker build -t invoiceiq .
docker run --env-file .env -p 8080:8080 invoiceiq
```

The image starts Streamlit on port `8080` and includes Tesseract OCR. For Cloud Run deployment, use [docs/gcp-deployment-guide.md](/Users/vijay/invoice_problem/docs/gcp-deployment-guide.md). Cloud Run local storage is ephemeral; production deployments must configure the documented persistent backup/storage strategy for SQLite and uploaded documents.

## Documentation

- [Architecture contract](/Users/vijay/invoice_problem/docs/architecture-contract.md)
- [Requirements matrix](/Users/vijay/invoice_problem/docs/requirements-matrix.md)
- [Canonical invoice schema](/Users/vijay/invoice_problem/docs/canonical-invoice-schema.md)
- [Decision statuses](/Users/vijay/invoice_problem/docs/decision-statuses.md)
- [Database schema and audit specification](/Users/vijay/invoice_problem/docs/database-schema.md)
- [Acceptance test matrix](/Users/vijay/invoice_problem/docs/acceptance-test-matrix.md)
- [Cloud Run deployment guide](/Users/vijay/invoice_problem/docs/gcp-deployment-guide.md)

## Security notes

- Store API keys in environment variables or a secret manager, never in source control.
- Treat invoice PDFs and extracted content as untrusted input.
- Do not log raw credentials or sensitive payment/banking data.
- Preserve original documents and extraction records; corrections must be recorded as auditable changes and trigger full revalidation.
