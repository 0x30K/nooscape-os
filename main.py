"""Nooscape — main entry point.

Usage:
    python main.py           Fast mode (max speed, no display)
    python main.py --watch   Watch mode (live terminal, 1 tick/sec)
    python main.py gravity post "task" --reward 10
    python main.py gravity list
    python main.py gravity history [--limit 20]
    python main.py gravity stats
"""
import argparse
import signal
import sys
import time

from rich.live import Live
from rich.console import Console

from simulation.runner import initialize_world, run_tick
from world.persistence import Database
from cli.observe import build_display
import config

# Graceful shutdown
_running = True


def _handle_sigint(sig, frame):
    global _running
    _running = False


signal.signal(signal.SIGINT, _handle_sigint)


def main():
    parser = argparse.ArgumentParser(description="Nooscape — Proof of Life")
    subparsers = parser.add_subparsers(dest="subcommand")

    # gravity subcommand — delegates to cli.gravity
    gravity_parser = subparsers.add_parser("gravity", help="Human bounty interface")
    gravity_sub = gravity_parser.add_subparsers(dest="gravity_command")

    gp = gravity_sub.add_parser("post")
    gp.add_argument("description", type=str)
    gp.add_argument("--reward", type=float, required=True)
    gp.add_argument("--db", default="nooscape.db")

    gl = gravity_sub.add_parser("list")
    gl.add_argument("--db", default="nooscape.db")

    gh = gravity_sub.add_parser("history")
    gh.add_argument("--limit", type=int, default=20)
    gh.add_argument("--db", default="nooscape.db")

    gs = gravity_sub.add_parser("stats")
    gs.add_argument("--db", default="nooscape.db")

    # simulation subcommand options (applied when no subcommand given)
    parser.add_argument(
        "--watch", action="store_true",
        help="Watch mode: live terminal display, 1 tick/sec",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for deterministic runs",
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Start fresh (ignore existing database)",
    )
    args = parser.parse_args()

    # Handle gravity subcommand
    if args.subcommand == "gravity":
        from cli.gravity import post_bounty, list_bounties, bounty_history, world_stats
        if args.gravity_command == "post":
            post_bounty(args.description, args.reward, args.db)
        elif args.gravity_command == "list":
            list_bounties(args.db)
        elif args.gravity_command == "history":
            bounty_history(args.db, args.limit)
        elif args.gravity_command == "stats":
            world_stats(args.db)
        else:
            gravity_parser.print_help()
        return

    # Set random seed if provided
    if args.seed is not None:
        import random
        random.seed(args.seed)

    console = Console()

    # Initialize database
    db = Database("nooscape.db")

    try:
        # Load or create world
        world = None
        if not args.fresh:
            world = db.load_latest()
            if world:
                console.print(f"[green]Resumed from tick {world.tick} with {len(world.get_living_agents())} living agents[/green]")

        if world is None:
            world = initialize_world()
            db.save_snapshot(world)
            console.print(f"[cyan]Created new world with {len(world.agents)} genesis agents[/cyan]")

        # Tick delay
        tick_delay = config.WATCH_TICK_DELAY if args.watch else config.FAST_TICK_DELAY

        # Event buffer for display
        recent_events = []

        if args.watch:
            _run_watch_mode(world, db, tick_delay, recent_events, console)
        else:
            _run_fast_mode(world, db, tick_delay, recent_events, console)

    finally:
        db.close()

    console.print("\n[yellow]Nooscape stopped.[/yellow]")


def _run_watch_mode(world, db, tick_delay, recent_events, console):
    """Run with live terminal display."""
    global _running

    with Live(build_display(world, recent_events), console=console, refresh_per_second=2) as live:
        while _running:
            world, events = run_tick(world)
            recent_events = (events + recent_events)[:20]

            # Log events to database
            for event in events:
                db.log_event(
                    event["tick"], event["event_type"],
                    event["agent_id"], event.get("details", {}),
                )

            # Save snapshot at intervals
            if world.tick % config.SNAPSHOT_INTERVAL == 0:
                db.save_snapshot(world)

            live.update(build_display(world, recent_events))

            # Check if all agents dead
            if not world.get_living_agents():
                console.print("[red]All agents have died. World is empty.[/red]")
                db.save_snapshot(world)
                break

            time.sleep(tick_delay)

    # Final save
    db.save_snapshot(world)


def _run_fast_mode(world, db, tick_delay, recent_events, console):
    """Run at max speed with periodic status output."""
    global _running
    start_time = time.time()
    last_report = 0

    while _running:
        world, events = run_tick(world)

        # Log events to database
        for event in events:
            db.log_event(
                event["tick"], event["event_type"],
                event["agent_id"], event.get("details", {}),
            )

        # Save snapshot at intervals
        if world.tick % config.SNAPSHOT_INTERVAL == 0:
            db.save_snapshot(world)

        # Print status every 1000 ticks
        if world.tick - last_report >= 1000:
            living = world.get_living_agents()
            elapsed = time.time() - start_time
            tps = world.tick / elapsed if elapsed > 0 else 0
            console.print(
                f"Tick {world.tick:>8,} | "
                f"Living: {len(living):>4} | "
                f"Dead: {len(world.agents) - len(living):>4} | "
                f"Minted: {world.total_tokens_minted:>10,.1f} | "
                f"TPS: {tps:>8,.0f}"
            )
            last_report = world.tick

        # Check if all agents dead
        if not world.get_living_agents():
            console.print("[red]All agents have died. World is empty.[/red]")
            db.save_snapshot(world)
            break

        time.sleep(tick_delay)

    # Final save
    db.save_snapshot(world)


if __name__ == "__main__":
    main()
