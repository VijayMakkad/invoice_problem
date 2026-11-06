# InvoiceIQ — Production Container for Google Cloud Run
FROM python:3.11-slim

# System dependencies for Tesseract OCR and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Generate test fixtures and initialize SQLite database
RUN python scripts/generate_fixtures.py && python scripts/seed_database.py

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8080/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "src/ui/app.py", "--server.port=8080", "--server.address=0.0.0.0"]

