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


def distribute_sun(world: WorldState) -> WorldState:
    """Mint SUN_TOKENS_PER_TICK and distribute equally among living agents.

    If there are no living agents, nothing is minted.
    Increments total_tokens_minted.
    """
    new_world = copy.deepcopy(world)
    living = [a for a in new_world.agents.values() if a.alive]

    if not living:
        return new_world

    share = config.SUN_TOKENS_PER_TICK / len(living)
    for agent in living:
        agent.tokens += share

    new_world.total_tokens_minted += config.SUN_TOKENS_PER_TICK
    return new_world


def check_deaths(world: WorldState) -> WorldState:
    """Kill any living agent whose tokens have reached zero.

    Sets alive=False and records died_tick.
    """
    new_world = copy.deepcopy(world)

    for agent in new_world.agents.values():
        if agent.alive and agent.tokens <= 0:
            agent.alive = False
            agent.died_tick = new_world.tick

    return new_world


def process_tick(world: WorldState) -> WorldState:
    """Process one full tick of world physics.

    Order: entropy → sun → deaths → increment tick.
    Returns a new WorldState. Never mutates the input.
    """
    new_world = apply_entropy(world)
    new_world = distribute_sun(new_world)
    new_world = check_deaths(new_world)
    new_world.tick = world.tick + 1
    return new_world
