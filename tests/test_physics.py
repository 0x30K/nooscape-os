"""Tests for the physics engine — the sacred seam.

Every test verifies purity: same input → same output, no side effects.
"""
import pytest
from world.state import create_agent, create_world, WorldState, Bounty, ServiceListing
from world.physics import (
    apply_entropy,
    distribute_sun,
    distribute_radiance,
    check_deaths,
    process_tick,
    process_bounty_payouts,
    process_service_transactions,
    apply_reputation,
    expire_bounties,
)
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

        expected_each = config.RADIANCE_PER_TICK / 2
        assert new_world.agents["a1"].tokens == 10.0 + expected_each
        assert new_world.agents["a2"].tokens == 10.0 + expected_each

    def test_tracks_total_minted(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)

        new_world = distribute_sun(world)

        assert new_world.total_tokens_minted == config.RADIANCE_PER_TICK

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

        assert new_world.agents["a1"].tokens == 10.0 + config.RADIANCE_PER_TICK
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


class TestWorkWeightedRadiance:
    def test_work_weighted_radiance_distributes_more_to_workers(self):
        """Agent with weight 3.0 gets more radiance than agent with weight 1.0."""
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)
        world.agents["a2"] = create_agent("a2", "Rex-0", tokens=10.0)

        work_weights = {"a1": 3.0, "a2": 1.0}
        new_world = distribute_radiance(world, work_weights)

        # a1 gets 3/4 of RADIANCE_PER_TICK, a2 gets 1/4
        assert new_world.agents["a1"].tokens > new_world.agents["a2"].tokens
        assert new_world.agents["a1"].tokens == pytest.approx(10.0 + config.RADIANCE_PER_TICK * 0.75)
        assert new_world.agents["a2"].tokens == pytest.approx(10.0 + config.RADIANCE_PER_TICK * 0.25)

    def test_work_weighted_radiance_fallback_when_no_work(self):
        """Equal split when all weights are 0."""
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)
        world.agents["a2"] = create_agent("a2", "Rex-0", tokens=10.0)

        work_weights = {"a1": 0.0, "a2": 0.0}
        new_world = distribute_radiance(world, work_weights)

        expected_each = config.RADIANCE_PER_TICK / 2
        assert new_world.agents["a1"].tokens == pytest.approx(10.0 + expected_each)
        assert new_world.agents["a2"].tokens == pytest.approx(10.0 + expected_each)

    def test_work_weighted_radiance_dead_agents_excluded(self):
        """Dead agents get no radiance even if in work_weights."""
        world = create_world()
        alive = create_agent("a1", "Ada-0", tokens=10.0)
        dead = create_agent("a2", "Rex-0", tokens=5.0)
        dead.alive = False
        world.agents["a1"] = alive
        world.agents["a2"] = dead

        # Give dead agent a weight — it should still get nothing
        work_weights = {"a1": 1.0, "a2": 3.0}
        new_world = distribute_radiance(world, work_weights)

        # Only a1 is living, so a1 gets all of RADIANCE_PER_TICK
        assert new_world.agents["a1"].tokens == pytest.approx(10.0 + config.RADIANCE_PER_TICK)
        assert new_world.agents["a2"].tokens == 5.0


class TestBountyPayouts:
    def _make_world_with_bounty(self, reward=20.0, status="claimed"):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)
        world.gravity_pool = 50.0
        bounty = Bounty(
            id="b1",
            description="do something",
            reward=reward,
            posted_by="human",
            posted_tick=0,
            expires_at_tick=100,
            status=status,
            claimed_by="a1",
        )
        world.bounties["b1"] = bounty
        return world

    def test_bounty_payout_transfers_tokens(self):
        """Bounty reward moves from gravity_pool to agent."""
        world = self._make_world_with_bounty(reward=20.0)

        new_world = process_bounty_payouts(world, completions=["b1"])

        assert new_world.agents["a1"].tokens == pytest.approx(10.0 + 20.0)
        assert new_world.gravity_pool == pytest.approx(50.0 - 20.0)

    def test_bounty_payout_marks_completed(self):
        """Bounty status becomes 'completed'."""
        world = self._make_world_with_bounty()
        world.tick = 5

        new_world = process_bounty_payouts(world, completions=["b1"])

        assert new_world.bounties["b1"].status == "completed"
        assert new_world.bounties["b1"].completed_tick == 5
        assert new_world.total_bounties_completed == 1
        assert new_world.agents["a1"].work_count == 1
        assert new_world.agents["a1"].total_tokens_earned == pytest.approx(20.0)

    def test_bounty_payout_skips_non_claimed(self):
        """Only bounties with status='claimed' are processed."""
        world = self._make_world_with_bounty(status="open")

        new_world = process_bounty_payouts(world, completions=["b1"])

        assert new_world.agents["a1"].tokens == 10.0
        assert new_world.gravity_pool == 50.0


class TestServiceTransactions:
    def _make_world_with_service(self, price=15.0, buyer_tokens=20.0, status="claimed"):
        world = create_world()
        world.agents["provider"] = create_agent("provider", "Pro-0", tokens=5.0)
        world.agents["buyer"] = create_agent("buyer", "Buy-0", tokens=buyer_tokens)
        service = ServiceListing(
            id="s1",
            provider_id="provider",
            description="some service",
            price=price,
            status=status,
            buyer_id="buyer",
        )
        world.services["s1"] = service
        return world

    def test_service_transaction_transfers_tokens(self):
        """Price moves from buyer to provider."""
        world = self._make_world_with_service(price=15.0, buyer_tokens=20.0)

        new_world = process_service_transactions(world, fulfillments=[("s1", "provider", "buyer")])

        assert new_world.agents["provider"].tokens == pytest.approx(5.0 + 15.0)
        assert new_world.agents["buyer"].tokens == pytest.approx(20.0 - 15.0)
        assert new_world.services["s1"].status == "fulfilled"
        assert new_world.total_services_fulfilled == 1
        assert new_world.agents["provider"].work_count == 1
        assert new_world.agents["buyer"].work_count == 1
        assert new_world.agents["provider"].total_tokens_earned == pytest.approx(15.0)

    def test_service_transaction_skipped_if_buyer_broke(self):
        """No transfer if buyer.tokens < service.price."""
        world = self._make_world_with_service(price=15.0, buyer_tokens=5.0)

        new_world = process_service_transactions(world, fulfillments=[("s1", "provider", "buyer")])

        assert new_world.agents["provider"].tokens == pytest.approx(5.0)
        assert new_world.agents["buyer"].tokens == pytest.approx(5.0)
        assert new_world.services["s1"].status == "claimed"
        assert new_world.total_services_fulfilled == 0


class TestReputation:
    def test_reputation_delta_applied(self):
        """Agent reputation increases by delta."""
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)
        world.agents["a1"].reputation = 2.0

        new_world = apply_reputation(world, reputation_deltas={"a1": 3.0})

        assert new_world.agents["a1"].reputation == pytest.approx(5.0)

    def test_reputation_floor_zero(self):
        """Reputation cannot go below 0."""
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)
        world.agents["a1"].reputation = 1.0

        new_world = apply_reputation(world, reputation_deltas={"a1": -5.0})

        assert new_world.agents["a1"].reputation == 0.0

    def test_reputation_dead_agents_unchanged(self):
        """Dead agents do not receive reputation changes."""
        world = create_world()
        dead = create_agent("a1", "Ada-0", tokens=0.0)
        dead.alive = False
        dead.reputation = 1.0
        world.agents["a1"] = dead

        new_world = apply_reputation(world, reputation_deltas={"a1": 5.0})

        assert new_world.agents["a1"].reputation == 1.0


class TestBountyPayoutsGuards:
    def _make_world_with_bounty(self, reward=20.0, status="claimed", agent_alive=True, gravity_pool=50.0):
        world = create_world()
        agent = create_agent("a1", "Ada-0", tokens=10.0)
        agent.alive = agent_alive
        world.agents["a1"] = agent
        world.gravity_pool = gravity_pool
        bounty = Bounty(
            id="b1",
            description="do something",
            reward=reward,
            posted_by="human",
            posted_tick=0,
            expires_at_tick=100,
            status=status,
            claimed_by="a1",
        )
        world.bounties["b1"] = bounty
        return world

    def test_bounty_payout_skips_when_pool_insufficient(self):
        """Payout is skipped when gravity_pool < bounty.reward."""
        world = self._make_world_with_bounty(reward=50.0, gravity_pool=10.0)

        new_world = process_bounty_payouts(world, completions=["b1"])

        assert new_world.bounties["b1"].status == "claimed"
        assert new_world.gravity_pool == pytest.approx(10.0)
        assert new_world.agents["a1"].tokens == pytest.approx(10.0)

    def test_bounty_payout_skips_dead_agent(self):
        """Payout is skipped when the completing agent is dead."""
        world = self._make_world_with_bounty(reward=20.0, agent_alive=False, gravity_pool=50.0)

        new_world = process_bounty_payouts(world, completions=["b1"])

        assert new_world.bounties["b1"].status == "claimed"
        assert new_world.gravity_pool == pytest.approx(50.0)
        assert new_world.agents["a1"].tokens == pytest.approx(10.0)


class TestServiceTransactionGuards:
    def _make_world_with_service(self, price=15.0, buyer_tokens=20.0, status="claimed",
                                  provider_alive=True, buyer_alive=True):
        world = create_world()
        provider = create_agent("provider", "Pro-0", tokens=5.0)
        provider.alive = provider_alive
        buyer = create_agent("buyer", "Buy-0", tokens=buyer_tokens)
        buyer.alive = buyer_alive
        world.agents["provider"] = provider
        world.agents["buyer"] = buyer
        service = ServiceListing(
            id="s1",
            provider_id="provider",
            description="some service",
            price=price,
            status=status,
            buyer_id="buyer",
        )
        world.services["s1"] = service
        return world

    def test_service_transaction_skips_dead_party(self):
        """Transaction is skipped when provider is dead."""
        world = self._make_world_with_service(price=15.0, buyer_tokens=20.0, provider_alive=False)

        new_world = process_service_transactions(world, fulfillments=[("s1", "provider", "buyer")])

        assert new_world.services["s1"].status == "claimed"
        assert new_world.agents["provider"].tokens == pytest.approx(5.0)
        assert new_world.agents["buyer"].tokens == pytest.approx(20.0)
        assert new_world.total_services_fulfilled == 0

    def test_service_transaction_skips_dead_buyer(self):
        """Transaction is skipped when buyer is dead."""
        world = self._make_world_with_service(price=15.0, buyer_tokens=20.0, buyer_alive=False)

        new_world = process_service_transactions(world, fulfillments=[("s1", "provider", "buyer")])

        assert new_world.services["s1"].status == "claimed"
        assert new_world.agents["provider"].tokens == pytest.approx(5.0)
        assert new_world.agents["buyer"].tokens == pytest.approx(20.0)
        assert new_world.total_services_fulfilled == 0


class TestExpireBounties:
    def _make_world_with_bounty(self, status="open", expires_at_tick=5, tick=5, reward=10.0):
        world = create_world()
        world.tick = tick
        world.gravity_pool = 100.0
        bounty = Bounty(
            id="b1",
            description="test bounty",
            reward=reward,
            posted_by="human",
            posted_tick=0,
            expires_at_tick=expires_at_tick,
            status=status,
            claimed_by=None,
        )
        world.bounties["b1"] = bounty
        return world

    def test_expires_open_bounty_past_deadline(self):
        """Open bounty with expires_at_tick <= world.tick becomes 'expired'."""
        world = self._make_world_with_bounty(status="open", expires_at_tick=5, tick=5)

        new_world = expire_bounties(world)

        assert new_world.bounties["b1"].status == "expired"

    def test_returns_reward_to_gravity_pool(self):
        """Expired bounty's reward is added back to gravity_pool."""
        world = self._make_world_with_bounty(status="open", expires_at_tick=5, tick=5, reward=10.0)

        new_world = expire_bounties(world)

        assert new_world.gravity_pool == pytest.approx(110.0)

    def test_does_not_expire_claimed_bounty(self):
        """Claimed bounty is NOT expired even past deadline."""
        world = self._make_world_with_bounty(status="claimed", expires_at_tick=5, tick=10)

        new_world = expire_bounties(world)

        assert new_world.bounties["b1"].status == "claimed"

    def test_does_not_expire_before_deadline(self):
        """Bounty with expires_at_tick > world.tick stays 'open'."""
        world = self._make_world_with_bounty(status="open", expires_at_tick=10, tick=5)

        new_world = expire_bounties(world)

        assert new_world.bounties["b1"].status == "open"

    def test_expire_bounties_immutable(self):
        """Original world is not mutated by expire_bounties."""
        world = self._make_world_with_bounty(status="open", expires_at_tick=5, tick=5)

        expire_bounties(world)

        assert world.bounties["b1"].status == "open"
        assert world.gravity_pool == pytest.approx(100.0)


class TestDeathSetsLifespan:
    def test_death_sets_lifespan(self):
        """When agent dies, lifespan = died_tick - born_tick."""
        world = create_world()
        world.tick = 10
        agent = create_agent("a1", "Ada-0", tokens=0.0, born_tick=3)
        world.agents["a1"] = agent

        new_world = check_deaths(world)

        assert new_world.agents["a1"].alive is False
        assert new_world.agents["a1"].died_tick == 10
        assert new_world.agents["a1"].lifespan == 10 - 3
