"""Tests for the world state data model."""
import pytest
from world.state import Agent, WorldState, create_agent, create_world


class TestAgent:
    def test_create_agent_defaults(self):
        agent = create_agent(agent_id="agent_001", name="Ada-0", tokens=20.0)
        assert agent.id == "agent_001"
        assert agent.name == "Ada-0"
        assert agent.tokens == 20.0
        assert agent.alive is True
        assert agent.born_tick == 0
        assert agent.died_tick is None
        assert agent.generation == 0
        assert agent.parent_id is None

    def test_create_agent_with_parent(self):
        agent = create_agent(
            agent_id="agent_002",
            name="Ada-1",
            tokens=10.0,
            born_tick=50,
            generation=1,
            parent_id="agent_001",
        )
        assert agent.generation == 1
        assert agent.parent_id == "agent_001"
        assert agent.born_tick == 50


class TestWorldState:
    def test_create_world_empty(self):
        world = create_world()
        assert world.tick == 0
        assert world.agents == {}
        assert world.total_tokens_minted == 0.0
        assert world.total_tokens_burned == 0.0

    def test_add_agent_to_world(self):
        world = create_world()
        agent = create_agent(agent_id="agent_001", name="Ada-0", tokens=20.0)
        world.agents[agent.id] = agent
        assert len(world.agents) == 1
        assert world.agents["agent_001"].name == "Ada-0"

    def test_get_living_agents(self):
        world = create_world()
        alive = create_agent(agent_id="a1", name="Ada-0", tokens=20.0)
        dead = create_agent(agent_id="a2", name="Rex-0", tokens=0.0)
        dead.alive = False
        world.agents["a1"] = alive
        world.agents["a2"] = dead
        living = world.get_living_agents()
        assert len(living) == 1
        assert living[0].id == "a1"

    def test_agent_to_dict_roundtrip(self):
        agent = create_agent(
            agent_id="agent_001", name="Ada-0", tokens=20.0,
            born_tick=5, generation=1, parent_id="agent_000",
        )
        d = agent.to_dict()
        restored = Agent.from_dict(d)
        assert restored.id == agent.id
        assert restored.name == agent.name
        assert restored.tokens == agent.tokens
        assert restored.generation == agent.generation
        assert restored.parent_id == agent.parent_id

    def test_world_to_dict_roundtrip(self):
        world = create_world()
        agent = create_agent(agent_id="a1", name="Ada-0", tokens=20.0)
        world.agents["a1"] = agent
        world.tick = 42
        world.total_tokens_minted = 100.0
        d = world.to_dict()
        restored = WorldState.from_dict(d)
        assert restored.tick == 42
        assert restored.total_tokens_minted == 100.0
        assert "a1" in restored.agents
        assert restored.agents["a1"].name == "Ada-0"
