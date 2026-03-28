"""Nooscape persistence layer — SQLite save/load for world state.

Single file database: nooscape.db
Two tables: snapshots (full world state) and events (birth, death, etc.)

Event types logged via log_event():
  Core lifecycle:
    "birth"               — agent was born
    "death"               — agent died
    "work"                — agent performed work
    "reproduce"           — agent reproduced

  Phase 1 economy events:
    "gravity_posted"      — human posted a bounty
    "bounty_claimed"      — agent claimed a bounty
    "bounty_completed"    — agent completed a bounty
    "service_posted"      — agent posted a service listing
    "service_fulfilled"   — agent fulfilled a service for another agent
    "reputation_changed"  — agent's reputation changed
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


def get_generation_metrics(db_path: str = "nooscape.db") -> dict:
    """Compute per-generation statistics from the latest snapshot.

    Returns a dict keyed by generation number (int):
    {
        0: {
            "count": int,                # total agents in this generation (living + dead)
            "alive": int,                # currently living
            "dead": int,                 # total dead
            "avg_lifespan": float,       # average ticks lived (dead agents only; None if no dead)
            "avg_tokens_earned": float,  # average total_tokens_earned
            "avg_reputation": float,     # average reputation
        },
        1: { ... },
        ...
    }

    Returns {} if no snapshots exist.
    """
    db = Database(db_path)
    try:
        world = db.load_latest()
    finally:
        db.close()

    if world is None:
        return {}

    # Group agents by generation
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for agent in world.agents.values():
        groups[agent.generation].append(agent)

    result = {}
    for gen, agents in groups.items():
        alive = [a for a in agents if a.alive]
        dead = [a for a in agents if not a.alive]
        dead_with_lifespan = [a for a in dead if a.lifespan is not None]

        avg_lifespan = (
            sum(a.lifespan for a in dead_with_lifespan) / len(dead_with_lifespan)
            if dead_with_lifespan
            else None
        )
        avg_tokens_earned = sum(a.total_tokens_earned for a in agents) / len(agents)
        avg_reputation = sum(a.reputation for a in agents) / len(agents)

        result[gen] = {
            "count": len(agents),
            "alive": len(alive),
            "dead": len(dead),
            "avg_lifespan": avg_lifespan,
            "avg_tokens_earned": avg_tokens_earned,
            "avg_reputation": avg_reputation,
        }

    return result


def get_bounty_history(db_path: str = "nooscape.db", limit: int = 20) -> list:
    """Return the most recent bounty-related events (posted, claimed, completed).

    Returns list of event dicts: {tick, event_type, agent_id, details}
    Sorted by tick descending (most recent first).
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT tick, event_type, agent_id, details
               FROM events
               WHERE event_type IN ('gravity_posted', 'bounty_claimed', 'bounty_completed')
               ORDER BY tick DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "tick": row["tick"],
            "event_type": row["event_type"],
            "agent_id": row["agent_id"],
            "details": json.loads(row["details"]),
        }
        for row in rows
    ]


def get_world_economy_summary(db_path: str = "nooscape.db") -> dict:
    """Return a summary of the world economy from the latest snapshot.

    Returns:
    {
        "tick": int,
        "living_agents": int,
        "dead_agents": int,
        "total_tokens_in_world": float,   # sum of tokens of all living agents
        "total_tokens_minted": float,
        "total_tokens_burned": float,
        "gravity_pool": float,
        "total_bounties_completed": int,
        "total_services_fulfilled": int,
        "open_bounties": int,             # count of bounties with status="open"
    }

    Returns {} if no snapshots exist.
    """
    db = Database(db_path)
    try:
        world = db.load_latest()
    finally:
        db.close()

    if world is None:
        return {}

    living = [a for a in world.agents.values() if a.alive]
    dead = [a for a in world.agents.values() if not a.alive]
    open_bounties = sum(1 for b in world.bounties.values() if b.status == "open")

    return {
        "tick": world.tick,
        "living_agents": len(living),
        "dead_agents": len(dead),
        "total_tokens_in_world": sum(a.tokens for a in living),
        "total_tokens_minted": world.total_tokens_minted,
        "total_tokens_burned": world.total_tokens_burned,
        "gravity_pool": world.gravity_pool,
        "total_bounties_completed": world.total_bounties_completed,
        "total_services_fulfilled": world.total_services_fulfilled,
        "open_bounties": open_bounties,
    }
