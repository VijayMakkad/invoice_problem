import sqlite3
import uuid
import json
from typing import List, Dict, Any, Optional

class AuditRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def append_event(
        self,
        entity_type: str,
        entity_id: str,
        event_type: str,
        actor: str,
        payload: Dict[str, Any]
    ) -> str:
        event_id = str(uuid.uuid4())
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO audit_events (event_id, entity_type, entity_id, event_type, actor, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                entity_type,
                entity_id,
                event_type,
                actor,
                json.dumps(payload, default=str),
            )
        )
        return event_id

    def list_by_entity(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at ASC",
            (entity_type, entity_id)
        )
        return [dict(r) for r in cursor.fetchall()]

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]

