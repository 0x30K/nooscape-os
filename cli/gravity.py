"""Gravity CLI — human interface for posting bounties (gravity events) into the world.

Usage:
    python -m cli.gravity post "Description of task" --reward 10.0 [--db nooscape.db]
    python -m cli.gravity list [--db nooscape.db]
    python -m cli.gravity history [--limit 20] [--db nooscape.db]
    python -m cli.gravity stats [--db nooscape.db]
"""
import argparse
from uuid import uuid4
from typing import Optional

import config
from world.state import Bounty, WorldState
from world.persistence import Database, get_world_economy_summary


def post_bounty(description: str, reward: float, db_path: str = "nooscape.db") -> Optional[Bounty]:
    """Post a new bounty into the world and return it, or None if no world exists."""
    db = Database(db_path)
    try:
        world = db.load_latest()
        if world is None:
            print("No world found. Run main.py first.")
            return None

        bounty = Bounty(
            id="bounty_" + uuid4().hex[:8],
            description=description,
            reward=reward,
            posted_by="human",
            posted_tick=world.tick,
            expires_at_tick=world.tick + config.BOUNTY_LIFETIME,
            status="open",
        )

        world.bounties[bounty.id] = bounty
        world.gravity_pool += reward
        world.total_gravity_tokens += reward

        db.save_snapshot(world)
        db.log_event(
            world.tick,
            "gravity_posted",
            "human",
            {
                "bounty_id": bounty.id,
                "reward": reward,
                "description": description[:50],
            },
        )
    finally:
        db.close()

    expires_at_tick = bounty.expires_at_tick
    print(
        f'Bounty posted: [{bounty.id}] "{description[:50]}" '
        f"— {reward} tokens (expires tick {expires_at_tick})"
    )
    return bounty


def list_bounties(db_path: str = "nooscape.db") -> None:
    """Print a table of all open bounties in the world."""
    db = Database(db_path)
    try:
        world = db.load_latest()
    finally:
        db.close()

    if world is None:
        print("No world found. Run main.py first.")
        return

    open_bounties = [b for b in world.bounties.values() if b.status == "open"]

    if not open_bounties:
        print("No open bounties.")
        return

    # Header
    print(f"{'ID':<20}  {'Description':<42}  {'Reward':>8}  {'Posted':>8}  {'Expires':>8}")
    print("-" * 96)
    for b in open_bounties:
        desc = b.description[:40]
        print(f"{b.id:<20}  {desc:<42}  {b.reward:>8.1f}  {b.posted_tick:>8}  {b.expires_at_tick:>8}")


def bounty_history(db_path: str = "nooscape.db", limit: int = 20) -> None:
    """Print a table of completed/expired/claimed bounties."""
    db = Database(db_path)
    try:
        world = db.load_latest()
    finally:
        db.close()

    if world is None:
        print("No world found. Run main.py first.")
        return

    terminal_statuses = {"completed", "expired", "claimed"}
    historical = [
        b for b in world.bounties.values()
        if b.status in terminal_statuses
    ]
    historical.sort(key=lambda b: b.posted_tick, reverse=True)
    historical = historical[:limit]

    if not historical:
        print("No bounty history.")
        return

    print(f"{'ID':<20}  {'Status':<12}  {'Description':<32}  {'Reward':>8}  {'Posted':>8}  {'Completed':>10}")
    print("-" * 102)
    for b in historical:
        desc = b.description[:30]
        completed = str(b.completed_tick) if b.completed_tick is not None else "-"
        print(
            f"{b.id:<20}  {b.status:<12}  {desc:<32}  {b.reward:>8.1f}  {b.posted_tick:>8}  {completed:>10}"
        )


def world_stats(db_path: str = "nooscape.db") -> None:
    """Print a summary of the world economy."""
    summary = get_world_economy_summary(db_path)

    if not summary:
        print("No world found. Run main.py first.")
        return

    # Load world to get bounties_done count
    db = Database(db_path)
    try:
        world = db.load_latest()
    finally:
        db.close()

    bounties_done = world.total_bounties_completed if world else 0
    services_done = world.total_services_fulfilled if world else 0

    print(f"World Economy — Tick {summary['tick']:,}")
    print(f"  Living agents:     {summary['living_agents']}")
    print(f"  Dead agents:       {summary['dead_agents']}")
    print(f"  Tokens in world:   {summary['total_tokens_in_world']:.1f}")
    print(f"  Total minted:      {summary['total_tokens_minted']:,.1f}")
    print(f"  Total burned:      {summary['total_tokens_burned']:,.1f}")
    print(f"  Gravity pool:      {summary['gravity_pool']:.1f}")
    print(f"  Open bounties:     {summary['open_bounties']}")
    print(f"  Bounties done:     {bounties_done}")
    print(f"  Services done:     {services_done}")


def main():
    parser = argparse.ArgumentParser(description="Nooscape gravity CLI")
    subparsers = parser.add_subparsers(dest="command")

    # post
    post_parser = subparsers.add_parser("post", help="Post a new bounty")
    post_parser.add_argument("description", type=str)
    post_parser.add_argument("--reward", type=float, required=True)
    post_parser.add_argument("--db", default="nooscape.db")

    # list
    list_parser = subparsers.add_parser("list", help="List open bounties")
    list_parser.add_argument("--db", default="nooscape.db")

    # history
    history_parser = subparsers.add_parser("history", help="View bounty history")
    history_parser.add_argument("--limit", type=int, default=20)
    history_parser.add_argument("--db", default="nooscape.db")

    # stats
    stats_parser = subparsers.add_parser("stats", help="World economy stats")
    stats_parser.add_argument("--db", default="nooscape.db")

    args = parser.parse_args()
    if args.command == "post":
        post_bounty(args.description, args.reward, args.db)
    elif args.command == "list":
        list_bounties(args.db)
    elif args.command == "history":
        bounty_history(args.db, args.limit)
    elif args.command == "stats":
        world_stats(args.db)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
