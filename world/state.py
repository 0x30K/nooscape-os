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
    reputation: float = 0.0
    work_count: int = 0
    total_tokens_earned: float = 0.0
    lifespan: Optional[int] = None

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
            "reputation": self.reputation,
            "work_count": self.work_count,
            "total_tokens_earned": self.total_tokens_earned,
            "lifespan": self.lifespan,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Agent":
        return cls(
            id=d["id"],
            name=d["name"],
            tokens=d["tokens"],
            alive=d.get("alive", True),
            born_tick=d.get("born_tick", 0),
            died_tick=d.get("died_tick"),
            generation=d.get("generation", 0),
            parent_id=d.get("parent_id"),
            reputation=d.get("reputation", 0.0),
            work_count=d.get("work_count", 0),
            total_tokens_earned=d.get("total_tokens_earned", 0.0),
            lifespan=d.get("lifespan"),
        )


@dataclass
class Bounty:
    """A task posted to the world for agents to complete in exchange for tokens."""
    id: str
    description: str
    reward: float
    posted_by: str
    posted_tick: int
    expires_at_tick: int
    status: str = "open"
    claimed_by: Optional[str] = None
    claimed_tick: Optional[int] = None
    completed_tick: Optional[int] = None
    output: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "reward": self.reward,
            "posted_by": self.posted_by,
            "posted_tick": self.posted_tick,
            "expires_at_tick": self.expires_at_tick,
            "status": self.status,
            "claimed_by": self.claimed_by,
            "claimed_tick": self.claimed_tick,
            "completed_tick": self.completed_tick,
            "output": self.output,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Bounty":
        return cls(
            id=d["id"],
            description=d["description"],
            reward=d["reward"],
            posted_by=d["posted_by"],
            posted_tick=d["posted_tick"],
            expires_at_tick=d["expires_at_tick"],
            status=d.get("status", "open"),
            claimed_by=d.get("claimed_by"),
            claimed_tick=d.get("claimed_tick"),
            completed_tick=d.get("completed_tick"),
            output=d.get("output"),
        )


@dataclass
class ServiceListing:
    """A service an agent offers to other agents or humans in exchange for tokens."""
    id: str
    provider_id: str
    description: str
    price: float
    status: str = "open"
    buyer_id: Optional[str] = None
    hired_tick: Optional[int] = None
    fulfilled_tick: Optional[int] = None
    output: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider_id": self.provider_id,
            "description": self.description,
            "price": self.price,
            "status": self.status,
            "buyer_id": self.buyer_id,
            "hired_tick": self.hired_tick,
            "fulfilled_tick": self.fulfilled_tick,
            "output": self.output,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ServiceListing":
        return cls(
            id=d["id"],
            provider_id=d["provider_id"],
            description=d["description"],
            price=d["price"],
            status=d.get("status", "open"),
            buyer_id=d.get("buyer_id"),
            hired_tick=d.get("hired_tick"),
            fulfilled_tick=d.get("fulfilled_tick"),
            output=d.get("output"),
        )


@dataclass
class WorldState:
    """The complete state of the world at a given tick."""
    tick: int = 0
    agents: dict[str, "Agent"] = field(default_factory=dict)
    total_tokens_minted: float = 0.0
    total_tokens_burned: float = 0.0
    bounties: dict[str, "Bounty"] = field(default_factory=dict)
    services: dict[str, "ServiceListing"] = field(default_factory=dict)
    gravity_pool: float = 0.0
    total_gravity_tokens: float = 0.0
    total_bounties_completed: int = 0
    total_services_fulfilled: int = 0

    def get_living_agents(self) -> list:
        """Return a list of all living agents."""
        return [a for a in self.agents.values() if a.alive]

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "agents": {aid: a.to_dict() for aid, a in self.agents.items()},
            "total_tokens_minted": self.total_tokens_minted,
            "total_tokens_burned": self.total_tokens_burned,
            "bounties": {bid: b.to_dict() for bid, b in self.bounties.items()},
            "services": {sid: s.to_dict() for sid, s in self.services.items()},
            "gravity_pool": self.gravity_pool,
            "total_gravity_tokens": self.total_gravity_tokens,
            "total_bounties_completed": self.total_bounties_completed,
            "total_services_fulfilled": self.total_services_fulfilled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorldState":
        agents = {aid: Agent.from_dict(ad) for aid, ad in d["agents"].items()}
        bounties = {
            bid: Bounty.from_dict(bd)
            for bid, bd in d.get("bounties", {}).items()
        }
        services = {
            sid: ServiceListing.from_dict(sd)
            for sid, sd in d.get("services", {}).items()
        }
        return cls(
            tick=d["tick"],
            agents=agents,
            total_tokens_minted=d.get("total_tokens_minted", 0.0),
            total_tokens_burned=d.get("total_tokens_burned", 0.0),
            bounties=bounties,
            services=services,
            gravity_pool=d.get("gravity_pool", 0.0),
            total_gravity_tokens=d.get("total_gravity_tokens", 0.0),
            total_bounties_completed=d.get("total_bounties_completed", 0),
            total_services_fulfilled=d.get("total_services_fulfilled", 0),
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
