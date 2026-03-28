"""Tests for the world state data model."""
import pytest
from world.state import Agent, Bounty, ServiceListing, WorldState, create_agent, create_world


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


class TestPhase1Fields:
    def test_agent_has_reputation_field(self):
        agent = create_agent(agent_id="a1", name="Ada-0", tokens=20.0)
        assert agent.reputation == 0.0

    def test_agent_has_work_count(self):
        agent = create_agent(agent_id="a1", name="Ada-0", tokens=20.0)
        assert agent.work_count == 0

    def test_agent_has_total_tokens_earned(self):
        agent = create_agent(agent_id="a1", name="Ada-0", tokens=20.0)
        assert agent.total_tokens_earned == 0.0

    def test_agent_lifespan_none_by_default(self):
        agent = create_agent(agent_id="a1", name="Ada-0", tokens=20.0)
        assert agent.lifespan is None

    def test_bounty_creation(self):
        bounty = Bounty(
            id="b1",
            description="Summarize the weather",
            reward=10.0,
            posted_by="human",
            posted_tick=5,
            expires_at_tick=105,
        )
        assert bounty.status == "open"
        assert bounty.claimed_by is None
        assert bounty.claimed_tick is None
        assert bounty.completed_tick is None
        assert bounty.output is None

    def test_bounty_roundtrip(self):
        bounty = Bounty(
            id="b2",
            description="Write a poem",
            reward=5.0,
            posted_by="agent_001",
            posted_tick=10,
            expires_at_tick=110,
            status="claimed",
            claimed_by="agent_002",
            claimed_tick=15,
            completed_tick=20,
            output="Roses are red...",
        )
        d = bounty.to_dict()
        restored = Bounty.from_dict(d)
        assert restored.id == bounty.id
        assert restored.description == bounty.description
        assert restored.reward == bounty.reward
        assert restored.posted_by == bounty.posted_by
        assert restored.posted_tick == bounty.posted_tick
        assert restored.expires_at_tick == bounty.expires_at_tick
        assert restored.status == bounty.status
        assert restored.claimed_by == bounty.claimed_by
        assert restored.claimed_tick == bounty.claimed_tick
        assert restored.completed_tick == bounty.completed_tick
        assert restored.output == bounty.output

    def test_service_listing_creation(self):
        service = ServiceListing(
            id="s1",
            provider_id="agent_001",
            description="Translation service",
            price=3.0,
        )
        assert service.status == "open"
        assert service.buyer_id is None
        assert service.hired_tick is None
        assert service.fulfilled_tick is None
        assert service.output is None

    def test_world_state_roundtrip_with_bounty(self):
        world = create_world()
        agent = create_agent(agent_id="a1", name="Ada-0", tokens=20.0)
        world.agents["a1"] = agent
        bounty = Bounty(
            id="b1",
            description="Do something useful",
            reward=8.0,
            posted_by="human",
            posted_tick=1,
            expires_at_tick=101,
        )
        world.bounties["b1"] = bounty
        world.gravity_pool = 8.0
        world.total_bounties_completed = 2

        d = world.to_dict()
        restored = WorldState.from_dict(d)

        assert "b1" in restored.bounties
        assert restored.bounties["b1"].description == "Do something useful"
        assert restored.bounties["b1"].reward == 8.0
        assert restored.bounties["b1"].status == "open"
        assert restored.gravity_pool == 8.0
        assert restored.total_bounties_completed == 2
