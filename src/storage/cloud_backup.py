import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional
from src.config.settings import settings

logger = logging.getLogger(__name__)

class CloudStorageBackupHook:
    """
    Experimental Cloud Storage Snapshot Backup Hook.
    Flushes the SQLite WAL log to the main file using PRAGMA wal_checkpoint(TRUNCATE)
    and uploads a point-in-time snapshot to Google Cloud Storage.
    """
    def __init__(self, db_path: str = settings.DATABASE_PATH, bucket_name: Optional[str] = None):
        self.db_path = db_path
        self.bucket_name = bucket_name or settings.GCS_BUCKET_NAME
        self.enabled = settings.ENABLE_GCS_BACKUP

    def checkpoint_and_upload(self, destination_blob: str = "snapshots/invoiceiq_latest.db") -> bool:
        if not self.enabled or not self.bucket_name:
            logger.info("Cloud storage backup is disabled or unconfigured.")
            return False

        try:
            # 1. Truncate WAL to write all transactions into the primary db file
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

            # 2. Upload using google-cloud-storage SDK if installed
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(destination_blob)
            blob.upload_from_filename(self.db_path)
            logger.info(f"Database snapshot successfully uploaded to gs://{self.bucket_name}/{destination_blob}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload database snapshot to GCS: {e}")
            return False

