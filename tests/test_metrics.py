"""Tests for world/metrics.py — generational metrics and evolution analysis."""
import pytest

from world.state import WorldState, Agent
from world.metrics import generation_report, evolution_proof


def _make_agent(
    agent_id: str,
    generation: int,
    alive: bool = True,
    lifespan=None,
    reputation: float = 0.0,
    total_tokens_earned: float = 0.0,
    parent_id=None,
    born_tick: int = 0,
) -> Agent:
    return Agent(
        id=agent_id,
        name=agent_id,
        tokens=10.0,
        alive=alive,
        born_tick=born_tick,
        died_tick=None if alive else born_tick + (lifespan or 0),
        generation=generation,
        parent_id=parent_id,
        reputation=reputation,
        work_count=0,
        total_tokens_earned=total_tokens_earned,
        lifespan=lifespan,
    )


# ---------------------------------------------------------------------------
# generation_report tests
# ---------------------------------------------------------------------------

def test_generation_report_empty_world():
    """Returns {} for a world with no agents."""
    world = WorldState(tick=0)
    result = generation_report(world)
    assert result == {}


def test_generation_report_groups_correctly():
    """Agents are grouped by generation and counts are correct."""
    world = WorldState(tick=100)
    world.agents["a0"] = _make_agent("a0", generation=0, alive=True)
    world.agents["a1"] = _make_agent("a1", generation=0, alive=False, lifespan=50)
    world.agents["a2"] = _make_agent("a2", generation=1, alive=True)
    world.agents["a3"] = _make_agent("a3", generation=1, alive=True)

    report = generation_report(world)

    assert set(report.keys()) == {0, 1}
    assert report[0]["count"] == 2
    assert report[0]["alive"] == 1
    assert report[0]["dead"] == 1
    assert report[1]["count"] == 2
    assert report[1]["alive"] == 2
    assert report[1]["dead"] == 0


def test_generation_report_avg_lifespan_dead_only():
    """avg_lifespan is None when a generation has no dead agents."""
    world = WorldState(tick=50)
    world.agents["a0"] = _make_agent("a0", generation=0, alive=True)
    world.agents["a1"] = _make_agent("a1", generation=1, alive=False, lifespan=80)

    report = generation_report(world)

    # Gen 0: all alive, no dead -> avg_lifespan is None
    assert report[0]["avg_lifespan"] is None
    # Gen 1: one dead with lifespan 80 -> avg_lifespan = 80
    assert report[1]["avg_lifespan"] == 80.0


# ---------------------------------------------------------------------------
# evolution_proof tests
# ---------------------------------------------------------------------------

def test_evolution_proof_detects_improvement():
    """PROVEN when gen 1 has better lifespan and reputation than gen 0."""
    world = WorldState(tick=2500)

    # Gen 0: dead agents with lower metrics
    for i in range(5):
        world.agents[f"g0_{i}"] = _make_agent(
            f"g0_{i}", generation=0, alive=False, lifespan=100, reputation=5.0
        )

    # Gen 1: dead agents with higher metrics
    for i in range(5):
        world.agents[f"g1_{i}"] = _make_agent(
            f"g1_{i}", generation=1, alive=False, lifespan=200, reputation=10.0
        )

    result = evolution_proof(world)
    assert "PROVEN" in result
    assert "INSUFFICIENT DATA" not in result


def test_evolution_proof_insufficient_data():
    """INSUFFICIENT DATA when only one generation exists."""
    world = WorldState(tick=500)

    for i in range(5):
        world.agents[f"a{i}"] = _make_agent(
            f"a{i}", generation=0, alive=False, lifespan=100, reputation=5.0
        )

    result = evolution_proof(world)
    assert "INSUFFICIENT DATA" in result
