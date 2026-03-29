"""Generational metrics and evolution analysis for Nooscape. Pure functions."""
from collections import defaultdict
from typing import Optional

from world.state import WorldState


def generation_report(world: WorldState) -> dict:
    """Return per-generation stats for all agents (living + dead).

    Returns:
    {
        0: {
            "count": int,
            "alive": int,
            "dead": int,
            "avg_lifespan": float or None,   # dead agents only; None if no dead
            "avg_tokens_earned": float,
            "avg_reputation": float,
            "avg_children": float,
        },
        ...
    }

    Returns {} if world has no agents.
    """
    if not world.agents:
        return {}

    # Group agents by generation
    groups: dict = defaultdict(list)
    for agent in world.agents.values():
        groups[agent.generation].append(agent)

    # Build a map of agent_id -> child count
    child_count: dict = defaultdict(int)
    for agent in world.agents.values():
        if agent.parent_id is not None:
            child_count[agent.parent_id] += 1

    result = {}
    for gen, agents in groups.items():
        alive = [a for a in agents if a.alive]
        dead = [a for a in agents if not a.alive]
        dead_with_lifespan = [a for a in dead if a.lifespan is not None]

        avg_lifespan: Optional[float] = (
            sum(a.lifespan for a in dead_with_lifespan) / len(dead_with_lifespan)
            if dead_with_lifespan
            else None
        )
        avg_tokens_earned = sum(a.total_tokens_earned for a in agents) / len(agents)
        avg_reputation = sum(a.reputation for a in agents) / len(agents)
        avg_children = sum(child_count[a.id] for a in agents) / len(agents)

        result[gen] = {
            "count": len(agents),
            "alive": len(alive),
            "dead": len(dead),
            "avg_lifespan": avg_lifespan,
            "avg_tokens_earned": avg_tokens_earned,
            "avg_reputation": avg_reputation,
            "avg_children": avg_children,
        }

    return result


def evolution_proof(world: WorldState) -> str:
    """Return a multi-line evolution report string.

    "PROVEN" if at least one consecutive gen pair (N -> N+1) where both have
    dead agents AND gen N+1 has strictly better avg_lifespan AND avg_reputation.
    Otherwise "INSUFFICIENT DATA".
    """
    report = generation_report(world)

    lines = [f"Evolution Report — Tick {world.tick}", ""]

    if not report:
        lines.append("Verdict: INSUFFICIENT DATA — need at least 2 generations with dead agents to measure evolution.")
        return "\n".join(lines)

    # Sort generations
    sorted_gens = sorted(report.keys())

    for gen in sorted_gens:
        data = report[gen]
        lifespan_str = (
            f"avg lifespan {data['avg_lifespan']:.0f} ticks"
            if data["avg_lifespan"] is not None
            else "avg lifespan N/A"
        )
        lines.append(
            f"Generation {gen}: {lifespan_str}, avg reputation {data['avg_reputation']:.1f} "
            f"({data['count']} agents, {data['dead']} dead)"
        )

    # Check for proven improvement
    proven = False
    for i in range(len(sorted_gens) - 1):
        n = sorted_gens[i]
        n1 = sorted_gens[i + 1]
        data_n = report[n]
        data_n1 = report[n1]

        # Both must have dead agents with lifespan data
        if data_n["avg_lifespan"] is None or data_n1["avg_lifespan"] is None:
            continue
        if data_n["dead"] == 0 or data_n1["dead"] == 0:
            continue

        if (
            data_n1["avg_lifespan"] > data_n["avg_lifespan"]
            and data_n1["avg_reputation"] > data_n["avg_reputation"]
        ):
            proven = True
            break

    lines.append("")
    if proven:
        lines.append(
            "Verdict: PROVEN — generation N+1 outperforms generation N on both lifespan and reputation."
        )
    else:
        lines.append(
            "Verdict: INSUFFICIENT DATA — need at least 2 generations with dead agents to measure evolution."
        )

    return "\n".join(lines)
