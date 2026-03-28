"""Tests for the simulation runner."""
import pytest
from world.state import create_world, create_agent
from simulation.runner import initialize_world, run_tick
import config


class TestInitializeWorld:
    def test_creates_genesis_agents(self):
        world = initialize_world()

        living = world.get_living_agents()
        assert len(living) == config.GENESIS_AGENT_COUNT

    def test_genesis_agents_have_starting_tokens(self):
        world = initialize_world()

        for agent in world.agents.values():
            assert agent.tokens == config.STARTING_TOKENS

    def test_genesis_agents_are_generation_zero(self):
        world = initialize_world()

        for agent in world.agents.values():
            assert agent.generation == 0
            assert agent.parent_id is None

    def test_genesis_agents_have_unique_ids(self):
        world = initialize_world()

        ids = [a.id for a in world.agents.values()]
        assert len(ids) == len(set(ids))


class TestRunTick:
    def test_advances_tick(self):
        world = initialize_world()

        new_world, events = run_tick(world)

        assert new_world.tick == 1

    def test_returns_events_list(self):
        world = initialize_world()

        new_world, events = run_tick(world)

        assert isinstance(events, list)

    def test_agents_can_work(self):
        """An agent below the danger threshold should work and gain tokens."""
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=5.0)

        new_world, events = run_tick(world)

        # Entropy: 5.0 - 4.0 = 1.0. Death check: 1.0 > 0, alive.
        # Sun (1 agent): 1.0 + 30.0 = 31.0. Post-entropy (1.0) < danger (35): work.
        # Work: 31.0 + 1.5 = 32.5
        assert new_world.agents["a1"].tokens == pytest.approx(32.5)

    def test_reproduction_creates_child(self):
        """Force a reproduction by giving agent high tokens and seeding random."""
        import random
        # Try many seeds until we get a reproduce
        child_created = False
        for seed in range(200):
            random.seed(seed)
            test_world = create_world()
            test_world.agents["a1"] = create_agent("a1", "Ada-0", tokens=50.0)
            new_world, events = run_tick(test_world)
            if len(new_world.agents) > 1:
                child_created = True
                # Verify child properties
                children = [a for a in new_world.agents.values() if a.id != "a1"]
                assert len(children) == 1
                child = children[0]
                assert child.generation == 1
                assert child.parent_id == "a1"
                assert child.tokens == config.CHILD_STARTING_TOKENS
                break

        assert child_created, "Reproduction never triggered across 200 random seeds"

    def test_dead_agents_dont_act(self):
        world = create_world()
        dead = create_agent("a1", "Ada-0", tokens=5.0)
        dead.alive = False
        world.agents["a1"] = dead

        new_world, events = run_tick(world)

        # Dead agent's tokens shouldn't change (no entropy, no sun, no actions)
        assert new_world.agents["a1"].tokens == 5.0
