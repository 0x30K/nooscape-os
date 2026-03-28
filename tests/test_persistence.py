"""Tests for SQLite persistence layer."""
import os
import pytest
from world.state import create_agent, create_world, Agent, Bounty
from world.persistence import Database, get_generation_metrics, get_bounty_history, get_world_economy_summary


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


class TestGetGenerationMetrics:
    def test_get_generation_metrics_empty_db(self, tmp_path):
        db_path = str(tmp_path / "empty.db")
        db = Database(db_path)
        db.close()
        result = get_generation_metrics(db_path)
        assert result == {}

    def test_get_generation_metrics_groups_by_generation(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)

        world = create_world()
        world.tick = 10

        # Gen 0 agents: one alive, one dead
        a1 = Agent(id="a1", name="Ada-0", tokens=10.0, alive=True, generation=0,
                   total_tokens_earned=50.0, reputation=2.0, born_tick=0)
        a2 = Agent(id="a2", name="Rex-0", tokens=0.0, alive=False, generation=0,
                   total_tokens_earned=30.0, reputation=1.0, born_tick=0, died_tick=8, lifespan=8)

        # Gen 1 agents: two alive
        a3 = Agent(id="a3", name="Zoe-1", tokens=20.0, alive=True, generation=1,
                   total_tokens_earned=40.0, reputation=3.0, born_tick=5)
        a4 = Agent(id="a4", name="Max-1", tokens=15.0, alive=True, generation=1,
                   total_tokens_earned=60.0, reputation=4.0, born_tick=5)

        world.agents = {"a1": a1, "a2": a2, "a3": a3, "a4": a4}
        db.save_snapshot(world)
        db.close()

        result = get_generation_metrics(db_path)

        assert 0 in result
        assert 1 in result

        gen0 = result[0]
        assert gen0["count"] == 2
        assert gen0["alive"] == 1
        assert gen0["dead"] == 1

        gen1 = result[1]
        assert gen1["count"] == 2
        assert gen1["alive"] == 2
        assert gen1["dead"] == 0

    def test_get_generation_metrics_avg_lifespan_dead_only(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)

        world = create_world()
        world.tick = 20

        # Gen 0: two dead agents with known lifespans
        a1 = Agent(id="a1", name="Ada-0", tokens=0.0, alive=False, generation=0,
                   total_tokens_earned=50.0, reputation=2.0, born_tick=0, died_tick=10, lifespan=10)
        a2 = Agent(id="a2", name="Rex-0", tokens=0.0, alive=False, generation=0,
                   total_tokens_earned=30.0, reputation=1.0, born_tick=0, died_tick=6, lifespan=6)

        # Gen 1: all alive (no dead) — avg_lifespan should be None
        a3 = Agent(id="a3", name="Zoe-1", tokens=20.0, alive=True, generation=1,
                   total_tokens_earned=40.0, reputation=3.0, born_tick=5)

        world.agents = {"a1": a1, "a2": a2, "a3": a3}
        db.save_snapshot(world)
        db.close()

        result = get_generation_metrics(db_path)

        gen0 = result[0]
        assert gen0["avg_lifespan"] == 8.0  # (10 + 6) / 2

        gen1 = result[1]
        assert gen1["avg_lifespan"] is None  # no dead agents


class TestGetBountyHistory:
    def test_get_bounty_history_empty(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.close()
        result = get_bounty_history(db_path)
        assert result == []

    def test_get_bounty_history_returns_recent_first(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)

        # Log some bounty events at different ticks
        db.log_event(5, "gravity_posted", "human", {"bounty_id": "b1"})
        db.log_event(10, "bounty_claimed", "a1", {"bounty_id": "b1"})
        db.log_event(15, "bounty_completed", "a1", {"bounty_id": "b1"})
        db.log_event(20, "gravity_posted", "human", {"bounty_id": "b2"})

        # Also log a non-bounty event that should be excluded
        db.log_event(12, "birth", "a2", {"name": "Zoe-1"})

        db.close()

        result = get_bounty_history(db_path)

        # Should only have bounty events, sorted by tick desc
        assert len(result) == 4
        assert result[0]["tick"] == 20
        assert result[0]["event_type"] == "gravity_posted"
        assert result[1]["tick"] == 15
        assert result[1]["event_type"] == "bounty_completed"
        assert result[2]["tick"] == 10
        assert result[2]["event_type"] == "bounty_claimed"
        assert result[3]["tick"] == 5

        # Verify no non-bounty events included
        event_types = [e["event_type"] for e in result]
        assert "birth" not in event_types

    def test_get_bounty_history_respects_limit(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)

        for i in range(10):
            db.log_event(i, "gravity_posted", "human", {"bounty_id": f"b{i}"})

        db.close()

        result = get_bounty_history(db_path, limit=3)
        assert len(result) == 3
        assert result[0]["tick"] == 9  # most recent first


class TestGetWorldEconomySummary:
    def test_get_world_economy_summary_empty(self, tmp_path):
        db_path = str(tmp_path / "empty.db")
        db = Database(db_path)
        db.close()
        result = get_world_economy_summary(db_path)
        assert result == {}

    def test_get_world_economy_summary_correct_fields(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)

        world = create_world()
        world.tick = 42
        world.total_tokens_minted = 500.0
        world.total_tokens_burned = 100.0
        world.gravity_pool = 25.0
        world.total_bounties_completed = 3
        world.total_services_fulfilled = 2

        # Two living agents
        a1 = Agent(id="a1", name="Ada-0", tokens=100.0, alive=True, generation=0,
                   total_tokens_earned=200.0, reputation=5.0, born_tick=0)
        a2 = Agent(id="a2", name="Rex-0", tokens=150.0, alive=True, generation=0,
                   total_tokens_earned=300.0, reputation=3.0, born_tick=0)

        # One dead agent (tokens not counted in total_tokens_in_world)
        a3 = Agent(id="a3", name="Old-0", tokens=0.0, alive=False, generation=0,
                   total_tokens_earned=50.0, reputation=1.0, born_tick=0, died_tick=10, lifespan=10)

        # Two open bounties, one completed
        b1 = Bounty(id="b1", description="Do X", reward=50.0, posted_by="human",
                    posted_tick=1, expires_at_tick=100, status="open")
        b2 = Bounty(id="b2", description="Do Y", reward=30.0, posted_by="human",
                    posted_tick=2, expires_at_tick=100, status="open")
        b3 = Bounty(id="b3", description="Done Z", reward=20.0, posted_by="human",
                    posted_tick=3, expires_at_tick=100, status="completed",
                    claimed_by="a1", completed_tick=15)

        world.agents = {"a1": a1, "a2": a2, "a3": a3}
        world.bounties = {"b1": b1, "b2": b2, "b3": b3}

        db.save_snapshot(world)
        db.close()

        result = get_world_economy_summary(db_path)

        assert result["tick"] == 42
        assert result["living_agents"] == 2
        assert result["dead_agents"] == 1
        assert result["total_tokens_in_world"] == 250.0  # 100 + 150
        assert result["total_tokens_minted"] == 500.0
        assert result["total_tokens_burned"] == 100.0
        assert result["gravity_pool"] == 25.0
        assert result["total_bounties_completed"] == 3
        assert result["total_services_fulfilled"] == 2
        assert result["open_bounties"] == 2
