"""Tests for SQLite persistence layer."""
import os
import pytest
from world.state import create_agent, create_world
from world.persistence import Database


@pytest.fixture
def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_nooscape.db")
    database = Database(db_path)
    yield database
    database.close()


class TestSnapshots:
    def test_save_and_load_snapshot(self, db):
        world = create_world()
        world.tick = 42
        agent = create_agent("a1", "Ada-0", tokens=15.5)
        world.agents["a1"] = agent
        world.total_tokens_minted = 100.0
        world.total_tokens_burned = 50.0

        db.save_snapshot(world)
        loaded = db.load_latest()

        assert loaded is not None
        assert loaded.tick == 42
        assert loaded.total_tokens_minted == 100.0
        assert loaded.total_tokens_burned == 50.0
        assert "a1" in loaded.agents
        assert loaded.agents["a1"].tokens == 15.5

    def test_load_latest_returns_most_recent(self, db):
        world1 = create_world()
        world1.tick = 10
        world1.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)
        db.save_snapshot(world1)

        world2 = create_world()
        world2.tick = 20
        world2.agents["a1"] = create_agent("a1", "Ada-0", tokens=5.0)
        db.save_snapshot(world2)

        loaded = db.load_latest()

        assert loaded.tick == 20
        assert loaded.agents["a1"].tokens == 5.0

    def test_load_latest_returns_none_when_empty(self, db):
        loaded = db.load_latest()
        assert loaded is None


class TestEvents:
    def test_log_and_retrieve_events(self, db):
        db.log_event(10, "birth", "a1", {"name": "Ada-0"})
        db.log_event(15, "death", "a2", {"name": "Rex-0"})

        events = db.get_events(from_tick=0, to_tick=20)

        assert len(events) == 2
        assert events[0]["event_type"] == "birth"
        assert events[1]["event_type"] == "death"

    def test_get_events_filters_by_tick_range(self, db):
        db.log_event(5, "birth", "a1", {})
        db.log_event(15, "death", "a1", {})
        db.log_event(25, "birth", "a2", {})

        events = db.get_events(from_tick=10, to_tick=20)

        assert len(events) == 1
        assert events[0]["tick"] == 15

    def test_get_recent_events(self, db):
        for i in range(20):
            db.log_event(i, "work", f"a{i}", {})

        events = db.get_recent_events(limit=5)

        assert len(events) == 5
        assert events[0]["tick"] == 19  # most recent first
