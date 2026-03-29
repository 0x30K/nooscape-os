"""Nooscape physics engine — THE SACRED SEAM.

RULES:
  1. Every function takes WorldState in, returns NEW WorldState out.
  2. No side effects. No file I/O. No print. No network.
  3. No randomness. Randomness belongs to the agent layer.
  4. Given the same input, always produces the same output.

This module is the future Rust rewrite target.
When that day comes, only this file changes.
"""
import copy
from world.state import WorldState
import config


def apply_entropy(world: WorldState) -> WorldState:
    """Drain ENTROPY_COST_PER_TICK tokens from every living agent.

    Tokens cannot go below zero. Dead agents are not drained.
    Increments total_tokens_burned by the amount actually drained.
    """
    new_world = copy.deepcopy(world)
    total_burned = 0.0

    for agent in new_world.agents.values():
        if not agent.alive:
            continue
        drain = min(agent.tokens, config.ENTROPY_COST_PER_TICK)
        agent.tokens -= drain
        total_burned += drain

    new_world.total_tokens_burned += total_burned
    return new_world


def distribute_radiance(world: WorldState, work_weights: dict = None) -> WorldState:
    """Distribute radiance tokens weighted by work completed this tick.

    work_weights: mapping of agent_id -> weight (0.0 for idle agents).
    Weights: completed bounty = 3.0, fulfilled service = 2.0, stub work = 1.0, idle = 0.0.

    If total_weight == 0 (all agents idle), falls back to equal split among living agents
    to prevent starvation during bootstrap ticks.
    """
    new_world = copy.deepcopy(world)
    living = [a for a in new_world.agents.values() if a.alive]

    if not living:
        return new_world

    if work_weights is None:
        work_weights = {}

    total_weight = sum(work_weights.get(a.id, 0.0) for a in living)

    if total_weight == 0:
        # Fallback: equal split among living agents
        share = config.RADIANCE_PER_TICK / len(living)
        for agent in living:
            agent.tokens += share
    else:
        for agent in living:
            weight = work_weights.get(agent.id, 0.0)
            agent.tokens += config.RADIANCE_PER_TICK * (weight / total_weight)

    new_world.total_tokens_minted += config.RADIANCE_PER_TICK
    return new_world


# Keep distribute_sun as an alias for backward compatibility with runner.py
def distribute_sun(world: WorldState) -> WorldState:
    """Mint RADIANCE_PER_TICK and distribute equally among living agents.

    If there are no living agents, nothing is minted.
    Increments total_tokens_minted.
    """
    return distribute_radiance(world, work_weights=None)


def check_deaths(world: WorldState) -> WorldState:
    """Kill any living agent whose tokens have reached zero.

    Sets alive=False, records died_tick, and sets lifespan.
    """
    new_world = copy.deepcopy(world)

    for agent in new_world.agents.values():
        if agent.alive and agent.tokens <= 0:
            agent.alive = False
            agent.died_tick = new_world.tick
            agent.lifespan = new_world.tick - agent.born_tick

    return new_world


def process_bounty_payouts(world: WorldState, completions: list = None) -> WorldState:
    """Pay out completed bounties.

    completions: list of bounty IDs completed this tick.
    For each: transfers bounty.reward from gravity_pool to agent's tokens,
    marks bounty status='completed', increments agent.work_count,
    increments agent.total_tokens_earned, increments world.total_bounties_completed.
    """
    if completions is None:
        completions = []

    new_world = copy.deepcopy(world)

    for bounty_id in completions:
        bounty = new_world.bounties.get(bounty_id)
        if bounty is None or bounty.status != "claimed":
            continue

        agent = new_world.agents.get(bounty.claimed_by)
        if agent is None or not agent.alive:
            continue

        if new_world.gravity_pool < bounty.reward:
            continue  # skip — pool is insolvent for this bounty

        # Transfer reward from gravity_pool to agent
        agent.tokens += bounty.reward
        new_world.gravity_pool -= bounty.reward
        agent.work_count += 1
        agent.total_tokens_earned += bounty.reward

        # Mark bounty as completed
        bounty.status = "completed"
        bounty.completed_tick = new_world.tick

        new_world.total_bounties_completed += 1

    return new_world


def process_service_transactions(world: WorldState, fulfillments: list = None) -> WorldState:
    """Process agent-to-agent service completions.

    fulfillments: list of (service_id, provider_id, buyer_id).
    Transfers service.price from buyer to provider,
    marks service status='fulfilled', increments both agents' work_count,
    increments provider's total_tokens_earned, increments world.total_services_fulfilled.
    """
    if fulfillments is None:
        fulfillments = []

    new_world = copy.deepcopy(world)

    for service_id, provider_id, buyer_id in fulfillments:
        service = new_world.services.get(service_id)
        if service is None or service.status != "claimed":
            continue

        provider = new_world.agents.get(provider_id)
        buyer = new_world.agents.get(buyer_id)
        if provider is None or not provider.alive or buyer is None or not buyer.alive:
            continue

        # Skip if buyer can't afford it
        if buyer.tokens < service.price:
            continue

        # Transfer tokens
        buyer.tokens -= service.price
        provider.tokens += service.price
        provider.total_tokens_earned += service.price

        # Increment work counts
        provider.work_count += 1
        buyer.work_count += 1

        # Mark service as fulfilled
        service.status = "fulfilled"
        service.fulfilled_tick = new_world.tick

        new_world.total_services_fulfilled += 1

    return new_world


def apply_reputation(world: WorldState, reputation_deltas: dict = None) -> WorldState:
    """Apply reputation changes to agents.

    reputation_deltas: mapping of agent_id -> delta (positive or negative).
    Reputation floor is 0.0 (cannot go negative).
    Only living agents receive reputation changes.
    """
    if reputation_deltas is None:
        reputation_deltas = {}

    new_world = copy.deepcopy(world)

    for agent_id, delta in reputation_deltas.items():
        agent = new_world.agents.get(agent_id)
        if agent is None or not agent.alive:
            continue
        agent.reputation = max(0.0, agent.reputation + delta)

    return new_world


def expire_bounties(world: WorldState) -> WorldState:
    """Expire bounties that have exceeded their lifetime.

    Bounties with status='open' and world.tick >= expires_at_tick become 'expired'.
    Their reward is returned to gravity_pool (stays in escrow pool).
    Claimed bounties are NOT expired (agent is working on them).
    """
    new_world = copy.deepcopy(world)

    for bounty in new_world.bounties.values():
        if bounty.status == "open" and new_world.tick >= bounty.expires_at_tick:
            bounty.status = "expired"
            new_world.gravity_pool += bounty.reward

    return new_world


def process_tick(
    world: WorldState,
    work_weights: dict = None,
    bounty_completions: list = None,
    service_fulfillments: list = None,
    reputation_deltas: dict = None,
) -> WorldState:
    """Process one full tick of world physics.

    Order:
    1. apply_entropy
    2. check_deaths  (sets lifespan on death)
    3. expire_bounties
    4. process_bounty_payouts
    5. process_service_transactions
    6. apply_reputation
    7. distribute_radiance (work-weighted)
    8. increment tick
    """
    new_world = apply_entropy(world)
    new_world = check_deaths(new_world)
    new_world = expire_bounties(new_world)
    new_world = process_bounty_payouts(new_world, bounty_completions)
    new_world = process_service_transactions(new_world, service_fulfillments)
    new_world = apply_reputation(new_world, reputation_deltas)
    new_world = distribute_radiance(new_world, work_weights)
    new_world.tick = world.tick + 1
    return new_world
