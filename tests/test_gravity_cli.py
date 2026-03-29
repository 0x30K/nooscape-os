"""Smoke tests for cli/gravity.py."""
import os
import tempfile

import pytest

from world.persistence import Database
from world.state import WorldState, Agent
from cli.gravity import post_bounty, list_bounties


def _make_temp_world(db_path: str) -> WorldState:
    """Create a minimal world and save it to the given db_path."""
    world = WorldState(tick=10)
    agent = Agent(
        id="agent_001",
        name="TestAgent",
        tokens=50.0,
        alive=True,
        born_tick=0,
        generation=0,
    )
    world.agents[agent.id] = agent
    world.total_tokens_minted = 100.0

    db = Database(db_path)
    try:
        db.save_snapshot(world)
    finally:
        db.close()

    return world


def test_post_bounty_adds_to_world():
    """post_bounty() should add the bounty to world.bounties and increase gravity_pool."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        _make_temp_world(db_path)

        bounty = post_bounty("Write a haiku about entropy", 15.0, db_path)

        assert bounty is not None, "post_bounty should return a Bounty"
        assert bounty.id.startswith("bounty_")
        assert bounty.reward == 15.0
        assert bounty.posted_by == "human"
        assert bounty.status == "open"

        # Reload world and verify persistence
        db = Database(db_path)
        try:
            world = db.load_latest()
        finally:
            db.close()

        assert bounty.id in world.bounties, "Bounty should be in world.bounties"
        assert world.gravity_pool == 15.0, "gravity_pool should be increased by reward"
        assert world.total_gravity_tokens == 15.0
    finally:
        os.unlink(db_path)


def test_list_bounties_no_crash():
    """list_bounties() on a missing DB path should not raise an exception."""
    # Use a path that definitely doesn't exist
    missing_path = "/tmp/nonexistent_nooscape_test_12345.db"
    # Should not raise — may print error or create empty db
    try:
        list_bounties(missing_path)
    except Exception as exc:
        pytest.fail(f"list_bounties raised an unexpected exception: {exc}")
    finally:
        # Clean up if the db was created
        if os.path.exists(missing_path):
            os.unlink(missing_path)
