import sqlite3
import uuid
from typing import Optional, Dict, Any


class DocumentRepository:
    """Persists immutable source documents and provider extraction payloads."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def store_source(
        self,
        document_hash: str,
        filename: str,
        mime_type: str,
        document_bytes: bytes,
        extracted_text: str,
        page_count: int,
        is_scanned: bool,
    ) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO source_documents (
                document_hash, filename, mime_type, document_bytes, extracted_text,
                page_count, is_scanned
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_hash,
                filename,
                mime_type,
                document_bytes,
                extracted_text,
                page_count,
                int(is_scanned),
            ),
        )

    def record_extraction(
        self,
        document_hash: str,
        provider_name: str,
        latency_ms: int,
        prompt_tokens: Optional[int],
        completion_tokens: Optional[int],
        raw_response_text: str,
    ) -> str:
        extraction_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO extraction_records (
                extraction_id, document_hash, provider_name, latency_ms,
                prompt_tokens, completion_tokens, raw_response_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                extraction_id,
                document_hash,
                provider_name,
                latency_ms,
                prompt_tokens,
                completion_tokens,
                raw_response_text,
            ),
        )
        return extraction_id

    def get_source_metadata(self, document_hash: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            """
            SELECT document_hash, filename, mime_type, page_count, is_scanned, created_at
            FROM source_documents WHERE document_hash = ?
            """,
            (document_hash,),
        ).fetchone()
        return dict(row) if row else None
