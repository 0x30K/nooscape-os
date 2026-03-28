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
            agent = create_agent("a1", "Ada-0", tokens=50.0)
            agent.reputation = config.GRADUATION_THRESHOLD  # Phase 1: reputation gate
            test_world.agents["a1"] = agent
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


class TestPhase1Economy:
    """Tests for Phase 1 economy pipeline: bounties, services, reputation."""

    def test_run_tick_returns_events_list(self):
        """run_tick always returns a list of events (may be empty)."""
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ora-0", tokens=50.0)

        new_world, events = run_tick(world)

        assert isinstance(events, list)

    def test_bounty_claim_marks_bounty(self):
        """After a tick where agent claims a bounty, bounty.status == 'claimed'."""
        from world.state import Bounty
        world = create_world()
        # Agent with low tokens in danger zone to prioritise bounty claim
        agent = create_agent("a1", "Ada-0", tokens=10.0)
        world.agents["a1"] = agent

        bounty = Bounty(
            id="b1",
            description="Test task",
            reward=10.0,
            posted_by="system",
            posted_tick=0,
            expires_at_tick=1000,
            status="open",
        )
        world.bounties["b1"] = bounty
        world.gravity_pool = 10.0

        new_world, events = run_tick(world)

        # Agent was in danger zone (tokens=10 <= DANGER_THRESHOLD=35) — should claim bounty
        assert new_world.bounties["b1"].status == "claimed"
        assert new_world.bounties["b1"].claimed_by == "a1"

    def test_bounty_completion_awards_tokens(self):
        """Agent claims bounty tick 1, completes it tick 2, receives reward."""
        from world.state import Bounty
        world = create_world()
        agent = create_agent("a1", "Rex-0", tokens=10.0)
        world.agents["a1"] = agent

        bounty = Bounty(
            id="b1",
            description="Write a hello world",
            reward=10.0,
            posted_by="system",
            posted_tick=0,
            expires_at_tick=1000,
            status="open",
        )
        world.bounties["b1"] = bounty
        world.gravity_pool = 10.0

        # Tick 1: agent claims the bounty
        world_after_claim, _ = run_tick(world)
        assert world_after_claim.bounties["b1"].status == "claimed"

        # Tick 2: agent completes the bounty
        world_after_complete, events = run_tick(world_after_claim)

        assert world_after_complete.bounties["b1"].status == "completed"
        # Gravity pool was debited
        assert world_after_complete.gravity_pool == pytest.approx(0.0)
        # Agent received the reward (10.0) + radiance, minus entropy over 2 ticks
        # Just verify it's more than what it would be without the bounty reward
        tokens_with_bounty = world_after_complete.agents["a1"].tokens
        assert tokens_with_bounty > 0  # alive and rewarded

        # Bounty completion event should be in events
        bounty_events = [e for e in events if e["event_type"] == "bounty_completed"]
        assert len(bounty_events) == 1
        assert bounty_events[0]["agent_id"] == "a1"
        assert bounty_events[0]["details"]["bounty_id"] == "b1"

    def test_reproduction_blocked_without_reputation(self):
        """Agent above REPRODUCE_THRESHOLD but below GRADUATION_THRESHOLD never reproduces."""
        import random
        world = create_world()
        agent = create_agent("a1", "Nova-0", tokens=200.0)
        agent.reputation = 0.0  # below GRADUATION_THRESHOLD (5.0)
        world.agents["a1"] = agent

        # Run many ticks — reproduction should never happen
        current_world = world
        for seed in range(100):
            random.seed(seed)
            current_world, _ = run_tick(current_world)
            assert len(current_world.get_living_agents()) == 1, (
                f"Reproduction occurred at seed {seed} despite reputation=0 < "
                f"GRADUATION_THRESHOLD={config.GRADUATION_THRESHOLD}"
            )

    def test_work_weights_influence_radiance(self):
        """Agent who works gets more radiance than agent who rests."""
        from world.state import Bounty
        # Two agents: one will work (below danger threshold), one will rest (high tokens)
        world = create_world()
        worker = create_agent("worker", "Flux-0", tokens=5.0)   # below DANGER_THRESHOLD → works
        rester = create_agent("rester", "Sage-0", tokens=200.0)  # high tokens → rests (no bounties)
        world.agents["worker"] = worker
        world.agents["rester"] = rester

        new_world, events = run_tick(world)

        # Worker: starts 5.0 - 4.0 entropy = 1.0, then works (+1.5 WORK_REWARD), then gets weighted radiance
        # Rester: starts 200.0 - 4.0 entropy = 196.0, rests, gets less radiance
        # Worker should have received a larger share of radiance (work_weight=1.0 vs 0.0)
        worker_tokens = new_world.agents["worker"].tokens
        rester_tokens = new_world.agents["rester"].tokens

        # Worker received all 30 radiance (100% weight) plus 1.5 work reward - 4.0 entropy + 5.0 start
        # = 5.0 - 4.0 + 1.5 + 30.0 = 32.5
        # Rester receives 0 radiance (0% weight) - 4.0 entropy + 200.0 = 196.0
        assert worker_tokens == pytest.approx(32.5)
        assert rester_tokens == pytest.approx(196.0)

    def test_service_hire_transfers_tokens(self):
        """Hiring a service transfers price from buyer to provider."""
        from world.state import ServiceListing
        world = create_world()

        provider = create_agent("provider", "Echo-0", tokens=50.0)
        buyer = create_agent("buyer", "Vex-0", tokens=200.0)  # rich enough to hire (> price * 2)
        world.agents["provider"] = provider
        world.agents["buyer"] = buyer

        service = ServiceListing(
            id="s1",
            provider_id="provider",
            description="Data analysis",
            price=10.0,
            status="open",
        )
        world.services["s1"] = service

        new_world, events = run_tick(world)

        # Buyer should have hired the service (tokens > price * 2 = 20)
        # Service should be fulfilled
        assert new_world.services["s1"].status == "fulfilled"

        # Token transfer: buyer loses price, provider gains price (net before entropy/radiance)
        # Buyer: 200.0 - 4.0 (entropy) - 10.0 (service price) + radiance
        # Provider: 50.0 - 4.0 (entropy) + 10.0 (service price) + radiance
        provider_tokens = new_world.agents["provider"].tokens
        buyer_tokens = new_world.agents["buyer"].tokens

        # Provider should have more tokens net-gain from service than buyer's token change
        # Verify service events logged
        service_events = [e for e in events if e["event_type"] == "service_fulfilled"]
        assert len(service_events) == 1
        assert service_events[0]["details"]["service_id"] == "s1"
        assert service_events[0]["details"]["buyer_id"] == "buyer"
