"""Nooscape simulation runner — the heartbeat of the world.

Orchestrates physics ticks, agent decisions, and action processing.
"""
import copy
import uuid
from world.state import WorldState, ServiceListing, create_agent, create_world
from world.physics import process_tick
from agents.agent import think, generate_name, generate_child_name, generate_work
import config


def initialize_world(llm=None) -> WorldState:
    """Create a fresh world with genesis agents.

    llm parameter is accepted for future use but ignored during initialization.
    """
    world = create_world()

    for i in range(config.GENESIS_AGENT_COUNT):
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        name = generate_name()
        agent = create_agent(
            agent_id=agent_id,
            name=name,
            tokens=config.STARTING_TOKENS,
            born_tick=0,
            generation=0,
        )
        world.agents[agent_id] = agent

    return world


def run_tick(world: WorldState, llm=None) -> tuple:
    """Run one complete tick: agent decisions then physics pipeline.

    Phase A: collect all agent decisions and apply agent-side token/state changes
             to a working copy of the world.
    Phase B: pass the modified world + collected weights/completions/fulfillments
             to process_tick (the authoritative physics pipeline).

    Returns (new_world_state, list_of_events).
    Events are dicts with keys: tick, event_type, agent_id, details.
    """
    events = []

    # Work on a deep copy so Phase A mutations don't corrupt the input world
    working_world = copy.deepcopy(world)

    # Accumulators for Phase B
    work_weights: dict[str, float] = {}
    bounty_completions: list[str] = []
    service_fulfillments: list[tuple] = []
    reputation_deltas: dict[str, float] = {}

    children_to_add = []

    # The tick number that will result after process_tick
    next_tick = world.tick + 1

    # -----------------------------------------------------------------------
    # Phase A — Agent Decisions
    # -----------------------------------------------------------------------
    for agent in working_world.get_living_agents():
        action = think(agent, working_world, llm)

        if action == "work":
            agent.tokens += config.WORK_REWARD
            work_weights[agent.id] = work_weights.get(agent.id, 0.0) + 1.0
            reputation_deltas[agent.id] = (
                reputation_deltas.get(agent.id, 0.0) + config.REPUTATION_PER_STUB_WORK
            )
            # Optional: log work events (high-volume but useful for debugging)
            events.append({
                "tick": next_tick,
                "event_type": "work",
                "agent_id": agent.id,
                "details": {"reward": config.WORK_REWARD},
            })

        elif action == "rest":
            work_weights[agent.id] = work_weights.get(agent.id, 0.0) + 0.0
            # rest: no token change, no reputation, no work weight

        elif action == "reproduce":
            if (
                agent.tokens >= config.REPRODUCTION_COST
                and agent.reputation >= config.GRADUATION_THRESHOLD
            ):
                agent.tokens -= config.REPRODUCTION_COST

                existing_children = sum(
                    1 for a in working_world.agents.values()
                    if a.parent_id == agent.id
                )
                child_number = existing_children + 1

                child_id = f"agent_{uuid.uuid4().hex[:8]}"
                child_name = generate_child_name(agent.name, child_number)
                child = create_agent(
                    agent_id=child_id,
                    name=child_name,
                    tokens=config.CHILD_STARTING_TOKENS,
                    born_tick=next_tick,
                    generation=agent.generation + 1,
                    parent_id=agent.id,
                )
                children_to_add.append(child)

                events.append({
                    "tick": next_tick,
                    "event_type": "birth",
                    "agent_id": child_id,
                    "details": {
                        "name": child_name,
                        "generation": agent.generation + 1,
                        "parent_id": agent.id,
                    },
                })

        elif action.startswith("claim_bounty:"):
            bounty_id = action.split(":", 1)[1]
            bounty = working_world.bounties.get(bounty_id)
            if bounty is not None and bounty.status == "open":
                bounty.status = "claimed"
                bounty.claimed_by = agent.id
                bounty.claimed_tick = world.tick

        elif action.startswith("complete_bounty:"):
            bounty_id = action.split(":", 1)[1]
            bounty = working_world.bounties.get(bounty_id)
            if bounty is not None and bounty.status == "claimed" and bounty.claimed_by == agent.id:
                # Generate the work output
                output = generate_work(bounty, llm)
                bounty.output = output
                # Record for physics to process payout
                bounty_completions.append(bounty_id)
                work_weights[agent.id] = work_weights.get(agent.id, 0.0) + 3.0
                reputation_deltas[agent.id] = (
                    reputation_deltas.get(agent.id, 0.0) + config.REPUTATION_PER_BOUNTY
                )
                events.append({
                    "tick": next_tick,
                    "event_type": "bounty_completed",
                    "agent_id": agent.id,
                    "details": {
                        "bounty_id": bounty_id,
                        "reward": bounty.reward,
                        "output_preview": output[:80] if output else "",
                    },
                })

        elif action.startswith("hire_service:"):
            service_id = action.split(":", 1)[1]
            service = working_world.services.get(service_id)
            if service is not None and service.status == "open" and service.provider_id != agent.id:
                provider = working_world.agents.get(service.provider_id)
                if provider is not None and provider.alive:
                    # Mark as claimed immediately
                    service.status = "claimed"
                    service.buyer_id = agent.id
                    service.hired_tick = world.tick
                    # Atomically fulfill in same tick
                    service_fulfillments.append((service_id, service.provider_id, agent.id))
                    # Provider gets work weight and reputation for fulfilling
                    work_weights[service.provider_id] = (
                        work_weights.get(service.provider_id, 0.0) + 2.0
                    )
                    reputation_deltas[service.provider_id] = (
                        reputation_deltas.get(service.provider_id, 0.0)
                        + config.REPUTATION_PER_SERVICE
                    )
                    events.append({
                        "tick": next_tick,
                        "event_type": "service_fulfilled",
                        "agent_id": service.provider_id,
                        "details": {
                            "service_id": service_id,
                            "price": service.price,
                            "buyer_id": agent.id,
                        },
                    })

        elif action.startswith("post_service:"):
            price_str = action.split(":", 1)[1]
            try:
                price = float(price_str)
            except ValueError:
                price = 1.0
            service_id = f"svc_{uuid.uuid4().hex[:8]}"
            service = ServiceListing(
                id=service_id,
                provider_id=agent.id,
                description=f"Service offered by {agent.name}",
                price=price,
                status="open",
            )
            working_world.services[service_id] = service

    # -----------------------------------------------------------------------
    # Phase B — Physics pipeline
    # -----------------------------------------------------------------------
    # Note: children are NOT added to working_world before process_tick.
    # Children born this tick don't participate in this tick's physics
    # (radiance, entropy, etc.) — they enter the world fresh next tick.
    new_world = process_tick(
        working_world,
        work_weights=work_weights,
        bounty_completions=bounty_completions,
        service_fulfillments=service_fulfillments,
        reputation_deltas=reputation_deltas,
    )

    # Now add children to the completed world state
    for child in children_to_add:
        new_world.agents[child.id] = child

    # Record deaths: compare new_world agents against working_world (pre-physics) state
    for agent_id, agent in new_world.agents.items():
        old_agent = working_world.agents.get(agent_id)
        if old_agent and old_agent.alive and not agent.alive:
            events.append({
                "tick": new_world.tick,
                "event_type": "death",
                "agent_id": agent_id,
                "details": {
                    "name": agent.name,
                    "tokens": agent.tokens,
                    "lifespan": agent.lifespan,
                },
            })

    return new_world, events
