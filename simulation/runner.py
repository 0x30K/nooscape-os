"""Nooscape simulation runner — the heartbeat of the world.

Orchestrates physics ticks, agent decisions, and action processing.
"""
import copy
import uuid
from world.state import WorldState, create_agent, create_world
from world.physics import process_tick, apply_entropy, distribute_sun, check_deaths
from agents.agent import think, generate_name, generate_child_name
import config


def initialize_world() -> WorldState:
    """Create a fresh world with genesis agents."""
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


def run_tick(world: WorldState) -> tuple:
    """Run one complete tick: physics + agent decisions + action processing.

    Returns (new_world_state, list_of_events).
    Events are dicts with keys: tick, event_type, agent_id, details.
    """
    events = []

    # 1. Apply physics step-by-step so decisions are made on post-entropy state
    # Entropy first — agents in the danger zone are identified after this step
    after_entropy = apply_entropy(world)

    # Snapshot post-entropy token levels to drive agent decisions
    post_entropy_tokens = {
        agent_id: agent.tokens
        for agent_id, agent in after_entropy.agents.items()
        if agent.alive
    }

    # Deaths happen BEFORE sun: starvation kills before sunlight can rescue
    after_deaths = check_deaths(after_entropy)
    after_sun = distribute_sun(after_deaths)
    new_world = after_sun
    new_world.tick = world.tick + 1

    # Record deaths from physics
    for agent_id, agent in new_world.agents.items():
        old_agent = world.agents.get(agent_id)
        if old_agent and old_agent.alive and not agent.alive:
            events.append({
                "tick": new_world.tick,
                "event_type": "death",
                "agent_id": agent_id,
                "details": {"name": agent.name, "generation": agent.generation},
            })

    # 2. Agent decisions and action processing — decisions based on post-entropy tokens
    # Build a view of each agent with post-entropy tokens for think()
    living = new_world.get_living_agents()
    children_to_add = []

    for agent in living:
        # Use post-entropy token snapshot for decision-making
        decision_agent = copy.copy(agent)
        decision_agent.tokens = post_entropy_tokens.get(agent.id, agent.tokens)
        action = think(decision_agent, new_world)

        if action == "work":
            agent.tokens += config.WORK_REWARD
            events.append({
                "tick": new_world.tick,
                "event_type": "work",
                "agent_id": agent.id,
                "details": {"reward": config.WORK_REWARD},
            })

        elif action == "reproduce":
            if agent.tokens >= config.REPRODUCTION_COST:
                agent.tokens -= config.REPRODUCTION_COST

                # Count existing children of this parent for naming
                existing_children = sum(
                    1 for a in new_world.agents.values()
                    if a.parent_id == agent.id
                )
                child_number = existing_children + 1

                child_id = f"agent_{uuid.uuid4().hex[:8]}"
                child_name = generate_child_name(agent.name, child_number)
                child = create_agent(
                    agent_id=child_id,
                    name=child_name,
                    tokens=config.CHILD_STARTING_TOKENS,
                    born_tick=new_world.tick,
                    generation=agent.generation + 1,
                    parent_id=agent.id,
                )
                children_to_add.append(child)

                events.append({
                    "tick": new_world.tick,
                    "event_type": "reproduce",
                    "agent_id": agent.id,
                    "details": {
                        "child_id": child_id,
                        "child_name": child_name,
                        "cost": config.REPRODUCTION_COST,
                    },
                })

        # 'rest' — no-op

    # Add children after iterating (don't modify dict during iteration)
    for child in children_to_add:
        new_world.agents[child.id] = child

    return new_world, events
