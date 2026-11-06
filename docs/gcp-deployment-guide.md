# GCP Cloud Run & DevOps Deployment Guide

This guide details containerization, GCP Cloud Run architecture, secret management, and billing isolation for InvoiceIQ.

## 1. Cloud Architecture

```
                  ┌───────────────────────────────────────────────┐
                  │                 Internet                      │
                  └──────────────────────┬────────────────────────┘
                                         │ HTTPS / Port 8080
                                         ▼
                  ┌───────────────────────────────────────────────┐
                  │            Google Cloud Run                   │
                  │   InvoiceIQ Container (Streamlit + FastAPI)   │
                  │   - Memory: 2GiB                              │
                  │   - CPU: 1 vCPU                               │
                  │   - Min instances: 0 (Scale to zero)          │
                  │   - Max instances: 2                          │
                  └───────┬───────────────────────────────┬───────┘
                          │                               │
                          ▼ Mounts                        ▼ Invokes
         ┌─────────────────────────────────┐   ┌───────────────────────────┐
         │      Secret Manager             │   │    Google Gemini API      │
         │ - GEMINI_API_KEY                │   │ (External API via Key)    │
         │ - APP_SECRET_KEY                │   └───────────────────────────┘
         └─────────────────────────────────┘
                          │
                          ▼ Persists
         ┌─────────────────────────────────┐
         │     GCS Bucket / Cloud SQL      │
         │  (Mounted via Cloud Storage     │
         │   FUSE or Cloud SQL Proxy)      │
         └─────────────────────────────────┘
```

## 2. Critical Billing Invariant: Gemini API vs GCP Free Credits
- **GCP Trial Credits ($300)** apply strictly to Google Cloud infrastructure: Compute Engine, Cloud Run, Artifact Registry, Cloud Logging, Secret Manager.
- **Gemini API Key**: If provisioned via Google AI Studio, usage falls under Google AI Studio free tier limits (e.g. 15 RPM / 1M TPM) or billed separately if attached to a direct AI Studio payment profile.
- **Never Assume GCP Credits Pay for AI Studio Gemini**: Ensure environment uses Vertex AI Gemini API endpoint if charging against GCP billing account credits, OR configure AI Studio Gemini API with strict rate-limiting / local Ollama fallback for 100% cost-free operation.

## 3. Storage Ephemerality on Cloud Run
- Cloud Run containers have **ephemeral filesystems**. Any file written to local `/tmp` or `./invoiceiq.db` is destroyed when instances scale to zero or restart.
- For production/staging:
  - Mount a Google Cloud Storage (GCS) bucket using Cloud Run volume mounts (GCS FUSE) for SQLite database and uploaded invoice PDFs.
  - Or configure SQLite backup synchronization to GCS on transaction commit.

## 4. Container Build & Deployment Commands

```bash
# 1. Build and push container to Artifact Registry
gcloud builds submit --tag gcr.io/${PROJECT_ID}/invoiceiq:latest

# 2. Deploy to Cloud Run with Secret Manager binding
gcloud run deploy invoiceiq \
    --image gcr.io/${PROJECT_ID}/invoiceiq:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-secrets=GEMINI_API_KEY=invoiceiq-gemini-key:latest \
    --set-env-vars=ENVIRONMENT=production,MAX_TOLERANCE_PERCENT=0.02 \
    --memory 2Gi \
    --cpu 1
```
