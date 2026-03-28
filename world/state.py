"""Nooscape world state — the canonical data model.

Agent: one record per agent (living or dead).
WorldState: the complete state of the world at a given tick.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Agent:
    """A single agent in the world."""
    id: str
    name: str
    tokens: float
    alive: bool = True
    born_tick: int = 0
    died_tick: Optional[int] = None
    generation: int = 0
    parent_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "tokens": self.tokens,
            "alive": self.alive,
            "born_tick": self.born_tick,
            "died_tick": self.died_tick,
            "generation": self.generation,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Agent":
        return cls(
            id=d["id"],
            name=d["name"],
            tokens=d["tokens"],
            alive=d["alive"],
            born_tick=d["born_tick"],
            died_tick=d.get("died_tick"),
            generation=d["generation"],
            parent_id=d.get("parent_id"),
        )


@dataclass
class WorldState:
    """The complete state of the world at a given tick."""
    tick: int = 0
    agents: dict = field(default_factory=dict)  # dict[str, Agent]
    total_tokens_minted: float = 0.0
    total_tokens_burned: float = 0.0

    def get_living_agents(self) -> list:
        """Return a list of all living agents."""
        return [a for a in self.agents.values() if a.alive]

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "agents": {aid: a.to_dict() for aid, a in self.agents.items()},
            "total_tokens_minted": self.total_tokens_minted,
            "total_tokens_burned": self.total_tokens_burned,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorldState":
        agents = {aid: Agent.from_dict(ad) for aid, ad in d["agents"].items()}
        return cls(
            tick=d["tick"],
            agents=agents,
            total_tokens_minted=d["total_tokens_minted"],
            total_tokens_burned=d["total_tokens_burned"],
        )


def create_agent(
    agent_id: str,
    name: str,
    tokens: float,
    born_tick: int = 0,
    generation: int = 0,
    parent_id: Optional[str] = None,
) -> Agent:
    """Factory function to create a new agent."""
    return Agent(
        id=agent_id,
        name=name,
        tokens=tokens,
        alive=True,
        born_tick=born_tick,
        died_tick=None,
        generation=generation,
        parent_id=parent_id,
    )


def create_world() -> WorldState:
    """Factory function to create a fresh empty world."""
    return WorldState()
