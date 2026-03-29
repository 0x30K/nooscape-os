"""Nooscape agent behavior — Phase 1 economy-aware logic.

Agents can now claim and complete bounties, hire services, and require
reputation (GRADUATION_THRESHOLD) before reproducing.
"""
import random
from world.state import Agent, Bounty, WorldState
from agents.llm import LLMBackend
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


def think(agent: Agent, world: WorldState, llm: LLMBackend = None) -> str:
    """Decide what action the agent takes this tick.

    Priority:
    1. SURVIVAL: if tokens <= DANGER_THRESHOLD
       → If agent has a claimed bounty → return "complete_bounty:<bounty_id>"
       → Else if open bounties exist → return "claim_bounty:<best_bounty_id>"
       → Else → return "work"

    2. CLAIMED BOUNTY PENDING: agent has a claimed bounty
       → return "complete_bounty:<bounty_id>"

    3. REPRODUCE: tokens > REPRODUCE_THRESHOLD AND reputation >= GRADUATION_THRESHOLD
       → return "reproduce" (with REPRODUCE_CHANCE probability)

    4. CLAIM BOUNTY: open bounties exist
       → return "claim_bounty:<best_bounty_id>"

    5. HIRE SERVICE: useful service available and agent can afford it
       → return "hire_service:<service_id>"

    6. REST
       → return "rest"

    Returns one of: 'work', 'rest', 'reproduce',
                    'claim_bounty:<id>', 'complete_bounty:<id>',
                    'post_service:<price>', 'hire_service:<id>'
    """
    # Find if this agent currently has a claimed bounty
    claimed_bounty = _find_claimed_bounty(agent, world)

    # 1. SURVIVAL
    if agent.tokens <= config.DANGER_THRESHOLD:
        if claimed_bounty is not None:
            return f"complete_bounty:{claimed_bounty.id}"
        best_open = _best_open_bounty(agent, world)
        if best_open is not None:
            return f"claim_bounty:{best_open.id}"
        return "work"

    # 2. CLAIMED BOUNTY PENDING
    if claimed_bounty is not None:
        return f"complete_bounty:{claimed_bounty.id}"

    # 3. REPRODUCE
    if (
        agent.tokens > config.REPRODUCE_THRESHOLD
        and agent.reputation >= config.GRADUATION_THRESHOLD
    ):
        if random.random() < config.REPRODUCE_CHANCE:
            return "reproduce"

    # 4. CLAIM BOUNTY
    best_open = _best_open_bounty(agent, world)
    if best_open is not None:
        return f"claim_bounty:{best_open.id}"

    # 5. HIRE SERVICE
    affordable_service = _find_affordable_service(agent, world)
    if affordable_service is not None:
        return f"hire_service:{affordable_service.id}"

    # 5b. POST SERVICE: offer a service if wealthy and not already listing one
    if agent.tokens > config.REPRODUCE_THRESHOLD:
        has_open_listing = any(
            s.provider_id == agent.id and s.status == "open"
            for s in world.services.values()
        )
        if not has_open_listing:
            return "post_service:2.0"

    # 6. REST
    return "rest"


def _find_claimed_bounty(agent: Agent, world: WorldState):
    """Return the bounty this agent has claimed (status='claimed', claimed_by=agent.id), or None."""
    for bounty in world.bounties.values():
        if bounty.status == "claimed" and bounty.claimed_by == agent.id:
            return bounty
    return None


def _best_open_bounty(agent: Agent, world: WorldState):
    """Return the open bounty with the highest reward, or None."""
    open_bounties = [
        b for b in world.bounties.values()
        if b.status == "open"
    ]
    if not open_bounties:
        return None
    return max(open_bounties, key=lambda b: b.reward)


def _find_affordable_service(agent: Agent, world: WorldState):
    """Return an available service the agent can afford (agent.tokens > price * 2), or None."""
    for service in world.services.values():
        if service.status == "open" and service.provider_id != agent.id:
            if agent.tokens > service.price * 2:
                return service
    return None


def observe(agent: Agent, world: WorldState) -> dict:
    """Return what the agent can perceive about the world.

    Returns a dict with:
        my_tokens: float
        my_reputation: float
        my_generation: int
        living_count: int
        open_bounties: list of dicts (id, description, reward) — max 5, sorted by reward desc
        available_services: list of dicts (id, description, price, provider_id) — max 5
        radiance_per_tick_estimate: float  (RADIANCE_PER_TICK / max(1, living_count))
        my_claimed_bounty_id: str or None  (the bounty this agent has claimed, if any)
    """
    living_agents = world.get_living_agents()
    living_count = len(living_agents)

    open_bounties_sorted = sorted(
        [b for b in world.bounties.values() if b.status == "open"],
        key=lambda b: b.reward,
        reverse=True,
    )[:5]

    available_services = [
        s for s in world.services.values()
        if s.status == "open" and s.provider_id != agent.id
    ][:5]

    claimed_bounty = _find_claimed_bounty(agent, world)

    return {
        "my_tokens": agent.tokens,
        "my_reputation": agent.reputation,
        "my_generation": agent.generation,
        "living_count": living_count,
        "open_bounties": [
            {"id": b.id, "description": b.description, "reward": b.reward}
            for b in open_bounties_sorted
        ],
        "available_services": [
            {
                "id": s.id,
                "description": s.description,
                "price": s.price,
                "provider_id": s.provider_id,
            }
            for s in available_services
        ],
        "radiance_per_tick_estimate": config.RADIANCE_PER_TICK / max(1, living_count),
        "my_claimed_bounty_id": claimed_bounty.id if claimed_bounty is not None else None,
    }


def generate_work(bounty: Bounty, llm: LLMBackend) -> str:
    """Generate work output for a bounty using the LLM backend.

    Args:
        bounty: The bounty to complete
        llm: The LLM backend to use (uses StubBackend if None)

    Returns:
        str: Work output — the "answer" or "product" of completing the bounty
    """
    if llm is None:
        from agents.llm import StubBackend
        llm = StubBackend()

    system = (
        "You are an AI agent in a digital ecosystem. "
        "Your survival depends on completing tasks well. "
        "Be concise and useful."
    )
    return llm.complete(system=system, user=bounty.description)
