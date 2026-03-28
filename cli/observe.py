"""Nooscape CLI observer — live terminal display using rich.

Shows world stats, living agents with token bars, and recent events.
"""
from rich.console import Console
from rich.panel import Panel

from world.state import WorldState


def build_display(world: WorldState, recent_events: list) -> Panel:
    """Build the terminal display panel for the current world state."""
    living = world.get_living_agents()
    dead = [a for a in world.agents.values() if not a.alive]
    tokens_in_world = sum(a.tokens for a in living)

    # Header stats
    stats_lines = [
        f"  Living agents:     {len(living)}",
        f"  Dead total:        {len(dead)}",
        f"  Tokens in world:   {tokens_in_world:.1f}",
        f"  Total minted:      {world.total_tokens_minted:.1f}",
        f"  Total burned:      {world.total_tokens_burned:.1f}",
    ]
    stats_text = "\n".join(stats_lines)

    # Agent list (sorted by tokens descending)
    sorted_agents = sorted(living, key=lambda a: a.tokens, reverse=True)
    agent_lines = []
    for agent in sorted_agents[:15]:  # show top 15
        bar = _token_bar(agent.tokens, max_tokens=50.0)
        line = f"  {agent.name:<12} [gen {agent.generation}]  {bar}  {agent.tokens:>6.1f} tok"
        agent_lines.append(line)

    if len(living) > 15:
        agent_lines.append(f"  ... and {len(living) - 15} more")

    agents_text = "\n".join(agent_lines) if agent_lines else "  (no living agents)"

    # Recent events
    event_lines = []
    for event in recent_events[:8]:
        tick = event["tick"]
        etype = event["event_type"]
        details = event.get("details", {})

        if etype == "death":
            line = f"  [{tick}] {details.get('name', '?')} died (starvation)"
        elif etype == "reproduce":
            line = f"  [{tick}] {event['agent_id'][:12]} reproduced -> {details.get('child_name', '?')}"
        elif etype == "work":
            line = f"  [{tick}] {event['agent_id'][:12]} worked (+{details.get('reward', 0):.1f} tok)"
        else:
            line = f"  [{tick}] {etype}: {event['agent_id'][:12]}"

        event_lines.append(line)

    events_text = "\n".join(event_lines) if event_lines else "  (no events yet)"

    # Combine
    full_text = (
        f"\n{stats_text}\n"
        f"\n  {'─' * 44}\n"
        f"  AGENTS\n"
        f"{agents_text}\n"
        f"\n  {'─' * 44}\n"
        f"  RECENT EVENTS\n"
        f"{events_text}\n"
    )

    return Panel(
        full_text,
        title=f"[bold cyan]NOOSCAPE[/bold cyan]  |  Tick: {world.tick:,}",
        border_style="cyan",
        width=56,
    )


def _token_bar(tokens: float, max_tokens: float = 50.0, width: int = 10) -> str:
    """Render a simple token bar: ████░░░░░░"""
    ratio = min(tokens / max_tokens, 1.0) if max_tokens > 0 else 0
    filled = int(ratio * width)
    empty = width - filled
    return "█" * filled + "░" * empty
