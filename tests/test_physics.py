"""Tests for the physics engine — the sacred seam.

Every test verifies purity: same input → same output, no side effects.
"""
import pytest
from world.state import create_agent, create_world, WorldState
from world.physics import apply_entropy, distribute_sun, check_deaths, process_tick
import config


class TestApplyEntropy:
    def test_drains_tokens_from_living_agents(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)
        world.agents["a2"] = create_agent("a2", "Rex-0", tokens=10.0)

        new_world = apply_entropy(world)

        assert new_world.agents["a1"].tokens == 20.0 - config.ENTROPY_COST_PER_TICK
        assert new_world.agents["a2"].tokens == 10.0 - config.ENTROPY_COST_PER_TICK

    def test_tokens_cannot_go_below_zero(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=0.1)

        new_world = apply_entropy(world)

        assert new_world.agents["a1"].tokens == 0.0

    def test_does_not_drain_dead_agents(self):
        world = create_world()
        dead = create_agent("a1", "Ada-0", tokens=5.0)
        dead.alive = False
        world.agents["a1"] = dead

        new_world = apply_entropy(world)

        assert new_world.agents["a1"].tokens == 5.0

    def test_tracks_total_burned(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)
        world.agents["a2"] = create_agent("a2", "Rex-0", tokens=20.0)

        new_world = apply_entropy(world)

        assert new_world.total_tokens_burned == config.ENTROPY_COST_PER_TICK * 2

    def test_does_not_mutate_original(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)
        original_tokens = world.agents["a1"].tokens

        apply_entropy(world)

        assert world.agents["a1"].tokens == original_tokens


class TestDistributeSun:
    def test_distributes_equally_among_living(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)
        world.agents["a2"] = create_agent("a2", "Rex-0", tokens=10.0)

        new_world = distribute_sun(world)

        expected_each = config.SUN_TOKENS_PER_TICK / 2
        assert new_world.agents["a1"].tokens == 10.0 + expected_each
        assert new_world.agents["a2"].tokens == 10.0 + expected_each

    def test_tracks_total_minted(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)

        new_world = distribute_sun(world)

        assert new_world.total_tokens_minted == config.SUN_TOKENS_PER_TICK

    def test_no_agents_no_distribution(self):
        world = create_world()

        new_world = distribute_sun(world)

        assert new_world.total_tokens_minted == 0.0

    def test_skips_dead_agents(self):
        world = create_world()
        alive = create_agent("a1", "Ada-0", tokens=10.0)
        dead = create_agent("a2", "Rex-0", tokens=5.0)
        dead.alive = False
        world.agents["a1"] = alive
        world.agents["a2"] = dead

        new_world = distribute_sun(world)

        assert new_world.agents["a1"].tokens == 10.0 + config.SUN_TOKENS_PER_TICK
        assert new_world.agents["a2"].tokens == 5.0

    def test_does_not_mutate_original(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)

        distribute_sun(world)

        assert world.agents["a1"].tokens == 10.0


class TestCheckDeaths:
    def test_kills_agent_at_zero_tokens(self):
        world = create_world()
        world.tick = 42
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=0.0)

        new_world = check_deaths(world)

        assert new_world.agents["a1"].alive is False
        assert new_world.agents["a1"].died_tick == 42

    def test_does_not_kill_agent_with_tokens(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=0.1)

        new_world = check_deaths(world)

        assert new_world.agents["a1"].alive is True
        assert new_world.agents["a1"].died_tick is None

    def test_does_not_mutate_original(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=0.0)

        check_deaths(world)

        assert world.agents["a1"].alive is True


class TestProcessTick:
    def test_increments_tick(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)

        new_world = process_tick(world)

        assert new_world.tick == 1

    def test_applies_entropy_then_deaths_then_sun(self):
        """An agent with exactly ENTROPY_COST tokens is drained to 0 and dies
        BEFORE sun is distributed. Starvation kills before sunlight can rescue."""
        world = create_world()
        # Agent has exactly entropy cost — after drain it hits 0, dies before sun
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=config.ENTROPY_COST_PER_TICK)

        new_world = process_tick(world)

        # Entropy drains to 0, death check fires at 0 (before sun), agent dies
        assert new_world.agents["a1"].alive is False
        assert new_world.agents["a1"].tokens == 0.0

    def test_does_not_mutate_original(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)

        process_tick(world)

        assert world.tick == 0
        assert world.agents["a1"].tokens == 20.0
