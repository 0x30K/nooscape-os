"""Tests for agent decision logic."""
import random
import pytest
from world.state import create_agent, create_world, Bounty, ServiceListing
from agents.agent import think, generate_name, generate_child_name, observe, generate_work
from agents.llm import StubBackend
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
        """With tokens above danger threshold, sufficient reputation, and favorable random, agent reproduces."""
        agent = create_agent("a1", "Ada-0", tokens=config.DANGER_THRESHOLD + 5.0)
        agent.reputation = config.GRADUATION_THRESHOLD  # Phase 1: reputation gate
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


class TestThinkBountyActions:
    def _make_bounty(self, bounty_id, reward=10.0, status="open", claimed_by=None):
        return Bounty(
            id=bounty_id,
            description=f"Do some task {bounty_id}",
            reward=reward,
            posted_by="human",
            posted_tick=0,
            expires_at_tick=999,
            status=status,
            claimed_by=claimed_by,
        )

    def test_think_claims_bounty_when_available(self):
        """Agent with enough tokens and open bounty returns claim_bounty action."""
        agent = create_agent("a1", "Ada-0", tokens=config.DANGER_THRESHOLD + 10.0)
        agent.reputation = config.GRADUATION_THRESHOLD  # enough reputation
        world = create_world()
        world.agents["a1"] = agent
        bounty = self._make_bounty("b1", reward=10.0, status="open")
        world.bounties["b1"] = bounty

        # Run many times — should always prefer bounty when well-resourced
        actions = set()
        for seed in range(50):
            random.seed(seed)
            actions.add(think(agent, world))

        assert any(a.startswith("claim_bounty:") for a in actions)

    def test_think_completes_claimed_bounty(self):
        """Agent with a claimed bounty returns complete_bounty action."""
        agent = create_agent("a1", "Ada-0", tokens=config.DANGER_THRESHOLD + 10.0)
        world = create_world()
        world.agents["a1"] = agent
        bounty = self._make_bounty("b2", reward=10.0, status="claimed", claimed_by="a1")
        world.bounties["b2"] = bounty

        action = think(agent, world)

        assert action == "complete_bounty:b2"

    def test_think_prefers_bounty_over_stub_work_when_desperate(self):
        """Desperate agent (below DANGER_THRESHOLD) with open bounty claims it, not work."""
        agent = create_agent("a1", "Ada-0", tokens=config.DANGER_THRESHOLD - 5.0)
        world = create_world()
        world.agents["a1"] = agent
        bounty = self._make_bounty("b3", reward=20.0, status="open")
        world.bounties["b3"] = bounty

        action = think(agent, world)

        assert action == "claim_bounty:b3"

    def test_think_falls_back_to_work_when_no_bounties(self):
        """Desperate agent with no bounties returns plain 'work'."""
        agent = create_agent("a1", "Ada-0", tokens=config.DANGER_THRESHOLD - 5.0)
        world = create_world()
        world.agents["a1"] = agent
        # No bounties in world

        action = think(agent, world)

        assert action == "work"

    def test_think_requires_reputation_to_reproduce(self):
        """Agent above REPRODUCE_THRESHOLD but below GRADUATION_THRESHOLD never reproduces."""
        agent = create_agent("a1", "Ada-0", tokens=config.REPRODUCE_THRESHOLD + 20.0)
        agent.reputation = config.GRADUATION_THRESHOLD - 0.1  # just below threshold
        world = create_world()
        world.agents["a1"] = agent

        for seed in range(100):
            random.seed(seed)
            action = think(agent, world)
            assert action != "reproduce", (
                f"Should not reproduce without enough reputation (seed={seed})"
            )


class TestObserve:
    def test_observe_returns_correct_structure(self):
        """observe() returns a dict with all required keys."""
        agent = create_agent("a1", "Ada-0", tokens=50.0)
        agent.generation = 2
        agent.reputation = 3.0
        world = create_world()
        world.agents["a1"] = agent

        result = observe(agent, world)

        assert isinstance(result, dict)
        assert "my_tokens" in result
        assert "my_reputation" in result
        assert "my_generation" in result
        assert "living_count" in result
        assert "open_bounties" in result
        assert "available_services" in result
        assert "radiance_per_tick_estimate" in result
        assert "my_claimed_bounty_id" in result

        assert result["my_tokens"] == 50.0
        assert result["my_reputation"] == 3.0
        assert result["my_generation"] == 2
        assert result["living_count"] == 1
        assert isinstance(result["open_bounties"], list)
        assert isinstance(result["available_services"], list)
        assert result["my_claimed_bounty_id"] is None


class TestGenerateWork:
    def test_generate_work_with_stub_returns_string(self):
        """generate_work() with StubBackend returns a non-empty string."""
        bounty = Bounty(
            id="b1",
            description="Summarize the key ideas in Hofstadter's GEB",
            reward=10.0,
            posted_by="human",
            posted_tick=0,
            expires_at_tick=999,
        )
        llm = StubBackend()

        result = generate_work(bounty, llm)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_work_output_relates_to_bounty(self):
        """StubBackend output contains a fragment of bounty description."""
        description = "Explain the halting problem in simple terms"
        bounty = Bounty(
            id="b2",
            description=description,
            reward=5.0,
            posted_by="human",
            posted_tick=0,
            expires_at_tick=999,
        )
        llm = StubBackend()

        result = generate_work(bounty, llm)

        # StubBackend returns first 60 chars of user prompt, which is the description
        assert description[:30] in result
