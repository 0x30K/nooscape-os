"""Nooscape web dashboard — FastAPI server.

Reads from SQLite (nooscape.db by default). Does not write to or interfere with simulation.

Run standalone:  python -m dashboard.app
Run with sim:    python main.py --dashboard
"""
import asyncio
import json
import os
import sys

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

# Ensure project root is importable
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from world.persistence import Database, get_world_economy_summary
from world.metrics import generation_report

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def create_app(db_path: str = "nooscape.db") -> FastAPI:
    app = FastAPI(title="Nooscape Dashboard")

    # Mount static files
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    # ------------------------------------------------------------------ #
    # GET /
    # ------------------------------------------------------------------ #
    @app.get("/")
    async def index():
        return FileResponse(os.path.join(_STATIC_DIR, "index.html"))

    # ------------------------------------------------------------------ #
    # GET /api/state
    # ------------------------------------------------------------------ #
    @app.get("/api/state")
    async def api_state():
        db = Database(db_path)
        try:
            world = db.load_latest()
        finally:
            db.close()

        if world is None:
            return {}

        living = [a for a in world.agents.values() if a.alive]
        dead = [a for a in world.agents.values() if not a.alive]

        return {
            "tick": world.tick,
            "living": len(living),
            "dead": len(dead),
            "total_minted": world.total_tokens_minted,
            "total_burned": world.total_tokens_burned,
            "gravity_pool": world.gravity_pool,
            "total_bounties_completed": world.total_bounties_completed,
            "total_services_fulfilled": world.total_services_fulfilled,
        }

    # ------------------------------------------------------------------ #
    # GET /api/agents
    # ------------------------------------------------------------------ #
    @app.get("/api/agents")
    async def api_agents():
        db = Database(db_path)
        try:
            world = db.load_latest()
        finally:
            db.close()

        if world is None:
            return []

        living = sorted(
            [a for a in world.agents.values() if a.alive],
            key=lambda a: a.tokens,
            reverse=True,
        )
        dead = sorted(
            [a for a in world.agents.values() if not a.alive],
            key=lambda a: (a.died_tick if a.died_tick is not None else 0),
            reverse=True,
        )[:20]

        def _fmt(agent):
            return {
                "id": agent.id,
                "name": agent.name,
                "generation": agent.generation,
                "tokens": agent.tokens,
                "reputation": agent.reputation,
                "alive": agent.alive,
                "work_count": agent.work_count,
                "total_tokens_earned": agent.total_tokens_earned,
                "born_tick": agent.born_tick,
                "died_tick": agent.died_tick,
                "lifespan": agent.lifespan,
                "parent_id": agent.parent_id,
            }

        return [_fmt(a) for a in living + dead]

    # ------------------------------------------------------------------ #
    # GET /api/events
    # ------------------------------------------------------------------ #
    @app.get("/api/events")
    async def api_events(limit: int = 50):
        db = Database(db_path)
        try:
            events = db.get_recent_events(limit)
        finally:
            db.close()
        return events

    # ------------------------------------------------------------------ #
    # GET /api/bounties
    # ------------------------------------------------------------------ #
    @app.get("/api/bounties")
    async def api_bounties():
        db = Database(db_path)
        try:
            world = db.load_latest()
        finally:
            db.close()

        if world is None:
            return {"open": [], "recent_completed": []}

        open_bounties = [
            b.to_dict()
            for b in world.bounties.values()
            if b.status == "open"
        ]

        completed = sorted(
            [b for b in world.bounties.values() if b.status == "completed"],
            key=lambda b: (b.completed_tick if b.completed_tick is not None else 0),
            reverse=True,
        )[:10]

        return {
            "open": open_bounties,
            "recent_completed": [b.to_dict() for b in completed],
        }

    # ------------------------------------------------------------------ #
    # GET /api/family-tree
    # ------------------------------------------------------------------ #
    @app.get("/api/family-tree")
    async def api_family_tree():
        db = Database(db_path)
        try:
            world = db.load_latest()
        finally:
            db.close()

        if world is None:
            return []

        agents = sorted(world.agents.values(), key=lambda a: a.born_tick)
        return [
            {
                "id": a.id,
                "name": a.name,
                "parent_id": a.parent_id,
                "generation": a.generation,
                "alive": a.alive,
            }
            for a in agents
        ]

    # ------------------------------------------------------------------ #
    # GET /api/metrics
    # ------------------------------------------------------------------ #
    @app.get("/api/metrics")
    async def api_metrics():
        db = Database(db_path)
        try:
            world = db.load_latest()
        finally:
            db.close()

        if world is None:
            return {}

        report = generation_report(world)
        # JSON keys must be strings
        return {str(k): v for k, v in report.items()}

    # ------------------------------------------------------------------ #
    # GET /api/stream  (SSE)
    # ------------------------------------------------------------------ #
    @app.get("/api/stream")
    async def stream(db: str = None):
        _db_path = db if db else db_path

        async def event_stream(path: str):
            last_tick = -1
            while True:
                try:
                    summary = get_world_economy_summary(path)
                    if summary and summary.get("tick", -1) != last_tick:
                        last_tick = summary["tick"]
                        yield f"data: {json.dumps(summary)}\n\n"
                except Exception:
                    pass
                await asyncio.sleep(2)

        return StreamingResponse(event_stream(_db_path), media_type="text/event-stream")

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
