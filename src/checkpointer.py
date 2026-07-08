import sqlite3
import json
import os
from typing import Dict, Any, Optional

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "checkpoints.db")
)

class SQLiteCheckpointer:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT PRIMARY KEY,
                    state TEXT,
                    events TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def save(self, thread_id: str, state: Dict[str, Any], events: list = None):
        if events is None:
            events = []
        serialized_state = self._serialize_state(state)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (thread_id, state, events) VALUES (?, ?, ?)",
                (thread_id, json.dumps(serialized_state, ensure_ascii=False), json.dumps(events, ensure_ascii=False))
            )
            conn.commit()
        finally:
            conn.close()

    def load(self, thread_id: str) -> Optional[tuple]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT state, events FROM checkpoints WHERE thread_id = ?", (thread_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0]), json.loads(row[1])
            return None
        finally:
            conn.close()

    def _serialize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        serialized = {}
        for k, v in state.items():
            if hasattr(v, "model_dump"):
                serialized[k] = v.model_dump()
            elif hasattr(v, "dict"):
                serialized[k] = v.dict()
            else:
                serialized[k] = v
        return serialized
