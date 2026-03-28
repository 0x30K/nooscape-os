"""Tests for agent decision logic."""
import random
import pytest
from world.state import create_agent, create_world
from agents.agent import think, generate_name, generate_child_name
import config


class TestThink:
    def test_works_when_tokens_below_danger(self):
        agent = create_agent("a1", "Ada-0", tokens=3.0)
        world = create_world()
        world.agents["a1"] = agent

        action = think(agent, world)

        assert action == "work"

    def test_works_when_tokens_just_below_danger(self):
        """Agent works when tokens are strictly below the danger threshold."""
        agent = create_agent("a1", "Ada-0", tokens=config.DANGER_THRESHOLD - 1.0)
        world = create_world()
        world.agents["a1"] = agent

        action = think(agent, world)

        assert action == "work"

    def test_works_when_tokens_moderate(self):
        """Agent works even at moderate token levels (danger threshold > reproduce
        threshold means agents work continuously until wealthy enough to reproduce)."""
        agent = create_agent("a1", "Ada-0", tokens=15.0)
        world = create_world()
        world.agents["a1"] = agent

        action = think(agent, world)

        assert action == "work"

    def test_can_reproduce_when_wealthy(self):
        """With tokens above danger threshold and favorable random, agent reproduces."""
        agent = create_agent("a1", "Ada-0", tokens=config.DANGER_THRESHOLD + 5.0)
        world = create_world()
        world.agents["a1"] = agent

        # Run multiple times to hit a reproduce
        actions = set()
        for seed in range(100):
            random.seed(seed)
            actions.add(think(agent, world))

        assert "reproduce" in actions

    def test_never_reproduces_below_threshold(self):
        """Even with favorable random, won't reproduce below threshold."""
        agent = create_agent("a1", "Ada-0", tokens=15.0)
        world = create_world()
        world.agents["a1"] = agent

        for seed in range(100):
            random.seed(seed)
            action = think(agent, world)
            assert action != "reproduce"


class TestNameGeneration:
    def test_generate_name_returns_string(self):
        name = generate_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_generate_child_name(self):
        name = generate_child_name("Ada-0", child_number=1)
        assert name == "Ada-1"

    def test_generate_child_name_from_child(self):
        name = generate_child_name("Ada-3", child_number=2)
        assert name == "Ada-2"

    def test_generate_child_name_preserves_stem(self):
        name = generate_child_name("Nova-0", child_number=5)
        assert name == "Nova-5"
