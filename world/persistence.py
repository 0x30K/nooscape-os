"""Nooscape persistence layer — SQLite save/load for world state.

Single file database: nooscape.db
Two tables: snapshots (full world state) and events (birth, death, etc.)
"""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from world.state import WorldState


class Database:
    """SQLite database for world state persistence."""

    def __init__(self, db_path: str = "nooscape.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                tick INTEGER PRIMARY KEY,
                world_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tick INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                details TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_events_tick ON events(tick);
        """)
        self.conn.commit()

    def save_snapshot(self, world: WorldState) -> None:
        """Save a full world state snapshot at the current tick."""
        world_json = json.dumps(world.to_dict())
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO snapshots (tick, world_json, timestamp) VALUES (?, ?, ?)",
            (world.tick, world_json, now),
        )
        self.conn.commit()

    def load_latest(self) -> Optional[WorldState]:
        """Load the most recent world state snapshot. Returns None if empty."""
        row = self.conn.execute(
            "SELECT world_json FROM snapshots ORDER BY tick DESC LIMIT 1"
        ).fetchone()

        if row is None:
            return None

        data = json.loads(row["world_json"])
        return WorldState.from_dict(data)

    def log_event(self, tick: int, event_type: str, agent_id: str, details: dict) -> None:
        """Log a world event (birth, death, work, reproduce)."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO events (tick, event_type, agent_id, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (tick, event_type, agent_id, json.dumps(details), now),
        )
        self.conn.commit()

    def get_events(self, from_tick: int, to_tick: int) -> list:
        """Get events within a tick range (inclusive)."""
        rows = self.conn.execute(
            "SELECT tick, event_type, agent_id, details FROM events WHERE tick >= ? AND tick <= ? ORDER BY tick",
            (from_tick, to_tick),
        ).fetchall()

        return [
            {
                "tick": row["tick"],
                "event_type": row["event_type"],
                "agent_id": row["agent_id"],
                "details": json.loads(row["details"]),
            }
            for row in rows
        ]

    def get_recent_events(self, limit: int = 10) -> list:
        """Get the most recent events, newest first."""
        rows = self.conn.execute(
            "SELECT tick, event_type, agent_id, details FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [
            {
                "tick": row["tick"],
                "event_type": row["event_type"],
                "agent_id": row["agent_id"],
                "details": json.loads(row["details"]),
            }
            for row in rows
        ]

    def close(self):
        """Close the database connection."""
        self.conn.close()
