"""Nooscape agent behavior — Phase 0 rule-based logic.

No LLM calls. The goal is to prove the physics works, not that agents
are intelligent. Smart agents come in Phase 1.
"""
import random
from world.state import Agent, WorldState
import config

# Name stems for genesis agents
_NAME_STEMS = [
    "Ada", "Rex", "Nova", "Zed", "Iris", "Bolt", "Sage", "Flux",
    "Echo", "Vex", "Ora", "Kip", "Lux", "Rune", "Axis", "Byte",
    "Coda", "Drift", "Ember", "Fern",
]

_name_counter = 0


def generate_name() -> str:
    """Generate a unique name for a genesis agent."""
    global _name_counter
    stem = _NAME_STEMS[_name_counter % len(_NAME_STEMS)]
    name = f"{stem}-0"
    _name_counter += 1
    return name


def generate_child_name(parent_name: str, child_number: int) -> str:
    """Generate a name for a child agent based on parent's name stem.

    'Ada-0' with child_number=1 → 'Ada-1'
    'Ada-3' with child_number=2 → 'Ada-2'
    """
    stem = parent_name.rsplit("-", 1)[0]
    return f"{stem}-{child_number}"


def think(agent: Agent, world: WorldState) -> str:
    """Decide what action the agent takes this tick.

    Priority:
    1. If tokens < DANGER_THRESHOLD → 'work'
    2. If tokens > REPRODUCE_THRESHOLD and random chance → 'reproduce'
    3. Otherwise → 'rest'

    Returns one of: 'work', 'rest', 'reproduce'
    """
    if agent.tokens <= config.DANGER_THRESHOLD:
        return "work"

    if agent.tokens > config.REPRODUCE_THRESHOLD:
        if random.random() < config.REPRODUCE_CHANCE:
            return "reproduce"

    return "rest"
