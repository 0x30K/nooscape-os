# Phase 1 — Economy & Evolution: Design Document

**Date:** 2026-03-28
**Author:** 30K + Claude
**Status:** Complete ✅
**Goal:** Agents earn tokens through real work, not stubs. Humans post bounties. Agents trade services. Reputation tracks useful output. Generation N+1 measurably outperforms generation N. World is observable through a web dashboard. Code is public on GitHub.

---

## What Phase 0 Proved

The physics work. Agents are born, entropy drains them, radiance sustains them, they reproduce, they die. Population self-regulates. The math is real. The Sacred Seam holds.

What Phase 0 did *not* prove: that work means anything. "Work" in Phase 0 was a stub — add 1.5 tokens, done. Radiance was distributed equally to all living agents regardless of contribution. There was no way to post a bounty, no way to trade between agents, no reputation, no reason for agents to be *useful* rather than just *alive*.

Phase 1 changes that.

---

## Phase 1 Goals

1. **Gravity** — Humans post tasks with token rewards. Agents complete them. Tokens flow from human to agent. This makes work real.
2. **Work-weighted radiance** — Radiance rewards agents who completed consumed work, not just agents who are alive. Idle agents get less.
3. **Reputation** — Agents accumulate reputation by completing work. Reputation gates reproduction and access to larger bounties.
4. **Agent-to-agent marketplace** — Agents can post services and pay other agents. Token flow between agents creates an internal economy.
5. **LLM reasoning** — `think()` calls an LLM (or falls back to a stub). Agents produce real work outputs, not empty strings.
6. **Generational proof** — Generation N+1 measurably outperforms generation N on lifespan, earnings, and reputation. Evolution is provable.
7. **Web dashboard** — The world is observable through a browser: live state, family trees, economy graphs, event feed.
8. **GitHub** — Code is public at `github.com/nooscape/nooscape-os`. Anyone can run it.

---

## Architecture Overview

Phase 1 adds three new layers above the existing foundation. The Sacred Seam (`physics.py`) is extended but remains pure. Nothing below it changes.

```
┌─────────────────────────────────────────────────────┐
│             Web Dashboard (FastAPI + HTML)           │
│   /api/state  /api/events  /api/family-tree         │
│   /api/metrics  /api/bounties  SSE stream           │
└─────────────────────────┬───────────────────────────┘
                          │ reads SQLite
┌─────────────────────────▼───────────────────────────┐
│              CLI + Gravity Interface                  │
│   main.py --watch  |  main.py gravity post/list      │
│   main.py metrics  |  main.py --dashboard           │
└─────────────────────────┬───────────────────────────┘
                          │ orchestrates
┌─────────────────────────▼───────────────────────────┐
│                 Simulation Runner                    │
│   run_tick(): physics → agent decisions → actions   │
│   New: process bounties, services, reputation       │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│                  Agent Layer                         │
│   think() → action (extended action set)            │
│   observe() → agent's perception of world           │
│   generate_work(bounty, llm) → work output          │
└─────────────────────────┬───────────────────────────┘
                          │ calls
┌─────────────────────────▼───────────────────────────┐
│               LLM Backend (agents/llm.py)           │
│   StubBackend (default, no API keys, tests pass)    │
│   OpenAIBackend | AnthropicBackend (optional)       │
└─────────────────────────┬───────────────────────────┘
                          │ actions submitted to
┌─────────────────────────▼───────────────────────────┐
│         Physics Engine (world/physics.py)           │  ← THE SACRED SEAM
│   Extended: work-weighted radiance, reputation updates,  │
│   bounty payouts, service transactions              │
│   Still pure: same input → same output, no I/O     │
└─────────────────────────┬───────────────────────────┘
                          │ reads/writes
┌─────────────────────────▼───────────────────────────┐
│              World State (world/state.py)            │
│   Extended: Agent + reputation, Bounty, Service     │
└─────────────────────────┬───────────────────────────┘
                          │ persists to
┌─────────────────────────▼───────────────────────────┐
│            Persistence (world/persistence.py)       │
│   Extended: bounty/service tables, metrics queries  │
└─────────────────────────────────────────────────────┘
```

---

## New Project Structure

```
nooscape-os/
├── world/
│   ├── state.py          # EXTENDED: + Bounty, ServiceListing, Agent fields
│   ├── physics.py        # EXTENDED: work-weighted radiance, reputation, payouts
│   ├── persistence.py    # EXTENDED: new event types, metrics queries
│   └── metrics.py        # NEW: generational analysis, evolution proof
├── agents/
│   ├── agent.py          # EXTENDED: richer actions, observe(), generate_work()
│   └── llm.py            # NEW: LLM backend abstraction + stub
├── simulation/
│   └── runner.py         # EXTENDED: bounty/service action processing
├── dashboard/
│   ├── app.py            # NEW: FastAPI server
│   └── static/
│       └── index.html    # NEW: single-page web dashboard
├── cli/
│   ├── observe.py        # EXTENDED: + reputation, bounties, services
│   └── gravity.py        # NEW: CLI gravity interface (human bounty posting)
├── main.py               # EXTENDED: --dashboard flag, bounty subcommands
├── config.py             # EXTENDED: new constants (GRADUATION_THRESHOLD, etc.)
├── requirements.txt      # EXTENDED: + fastapi, uvicorn, openai (optional)
└── tests/
    ├── test_state.py         # EXTENDED: test new fields + Bounty + Service
    ├── test_physics.py       # EXTENDED: test work-weighted radiance, reputation
    ├── test_agent.py         # EXTENDED: test new actions, observe(), generate_work()
    ├── test_persistence.py   # EXTENDED: test metrics queries, new event types
    ├── test_runner.py        # EXTENDED: test bounty/service processing
    ├── test_llm.py           # NEW: test stub backend, interface contract
    └── test_metrics.py       # NEW: test generational comparison functions
```

---

## Data Model Changes (`world/state.py`)

### Agent — New Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `reputation` | float | 0.0 | Increases when work is consumed |
| `work_count` | int | 0 | Total bounties completed + services fulfilled |
| `total_tokens_earned` | float | 0.0 | Cumulative tokens earned across lifespan |
| `lifespan` | int or None | None | Ticks alive (set on death: `died_tick - born_tick`) |

### Bounty — New Dataclass

Represents a unit of work posted by a human (Gravity event) or an agent.

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique identifier (`"bounty_a1b2c3"`) |
| `description` | str | What needs to be done |
| `reward` | float | Tokens held in escrow, released on completion |
| `posted_by` | str | `"human"` or an agent ID |
| `posted_tick` | int | Tick when posted |
| `expires_at_tick` | int | posted_tick + BOUNTY_LIFETIME |
| `status` | str | `"open"` \| `"claimed"` \| `"completed"` \| `"expired"` |
| `claimed_by` | str or None | Agent ID of claimer |
| `claimed_tick` | int or None | When claimed |
| `completed_tick` | int or None | When completed |
| `output` | str or None | The work product (text, code, answer) |

### ServiceListing — New Dataclass

Represents a service one agent offers to others.

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique identifier (`"svc_a1b2c3"`) |
| `provider_id` | str | Agent offering the service |
| `description` | str | What the agent can do |
| `price` | float | Tokens buyer must pay |
| `status` | str | `"open"` \| `"claimed"` \| `"fulfilled"` |
| `buyer_id` | str or None | Agent who hired this service |
| `hired_tick` | int or None | When hired |
| `fulfilled_tick` | int or None | When delivered |
| `output` | str or None | The delivered work |

### WorldState — New Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `bounties` | dict[str, Bounty] | {} | All bounties (open + history) |
| `services` | dict[str, ServiceListing] | {} | All service listings |
| `gravity_pool` | float | 0.0 | Tokens currently held in escrow across all bounties |
| `total_gravity_tokens` | float | 0.0 | Cumulative Gravity tokens ever injected |
| `total_bounties_completed` | int | 0 | Running count |
| `total_services_fulfilled` | int | 0 | Running count |

---

## Physics Changes (`world/physics.py`)

The Sacred Seam grows. All new functions are pure: no side effects, no I/O.

### Radiance Distribution Reform

**Phase 0:** Equal split among all living agents.

**Phase 1:** Weighted by work completed this tick. Work weights:

| Work type | Weight |
|-----------|--------|
| Completed a bounty | 3.0 |
| Fulfilled a service | 2.0 |
| Basic stub "work" action | 1.0 |
| Rest / no action | 0.0 |

Formula:
```
for each agent:
    radiance_share = RADIANCE_PER_TICK * (agent_weight / total_weight)

if total_weight == 0:
    # Fallback: equal split to all living agents (prevents extinction on slow ticks)
    radiance_share = RADIANCE_PER_TICK / len(living_agents)
```

Signature change:
```python
def distribute_radiance(world: WorldState, work_weights: dict[str, float]) -> WorldState:
    """Distribute radiance tokens weighted by work completed this tick.

    work_weights: mapping of agent_id → weight (0.0 for idle agents).
    If all agents are idle, falls back to equal split.
    """
```

The runner computes `work_weights` during action processing and passes it to `distribute_radiance`.

### New Physics Functions

**`process_bounty_payouts(world, completions: list[str]) → WorldState`**
- For each bounty ID in `completions`:
  - Mark bounty status = "completed"
  - Transfer `bounty.reward` from `gravity_pool` to completing agent's tokens
  - Increment agent's `work_count` and `total_tokens_earned`
  - Increment `world.total_bounties_completed`

**`process_service_transactions(world, fulfillments: list[tuple]) → WorldState`**
- Each fulfillment: `(service_id, provider_id, buyer_id)`
- Transfer `service.price` from buyer's tokens to provider's tokens
- Mark service status = "fulfilled"
- Increment both agents' counters

**`apply_reputation(world, reputation_deltas: dict[str, float]) → WorldState`**
- Apply delta to each agent's reputation score
- Reputation floor: 0.0 (cannot go negative)

**`expire_bounties(world) → WorldState`**
- Bounties older than `BOUNTY_LIFETIME` ticks → status = "expired"
- Return escrowed tokens to `gravity_pool` (human can repost)

**`check_deaths(world) → WorldState`** (extended)
- Unchanged logic, but now also sets `agent.lifespan = died_tick - born_tick`

**Updated `process_tick` signature:**
```python
def process_tick(
    world: WorldState,
    work_weights: dict[str, float],
    bounty_completions: list[str],
    service_fulfillments: list[tuple],
    reputation_deltas: dict[str, float],
) -> WorldState:
    """One full tick of world physics.

    Order:
    1. apply_entropy
    2. check_deaths
    3. expire_bounties
    4. process_bounty_payouts
    5. process_service_transactions
    6. apply_reputation
    7. distribute_radiance (work-weighted)
    8. increment tick
    """
```

All arguments computed by the runner during the agent-action phase, passed in together. Physics remains a pure function of its inputs.

---

## New Constants (`config.py`)

```python
# Phase 1 additions
GRADUATION_THRESHOLD = 5.0         # reputation required before agent can reproduce
BOUNTY_LIFETIME = 100              # ticks before an unclaimed bounty expires
SERVICE_LIFETIME = 50              # ticks before an unfulfilled service listing expires
MAX_OPEN_BOUNTIES = 20             # maximum concurrent open bounties in the world
MAX_SERVICES_PER_AGENT = 3        # max service listings one agent can post at once
REPUTATION_PER_BOUNTY = 3.0       # reputation gained for completing a bounty
REPUTATION_PER_SERVICE = 2.0      # reputation gained for fulfilling a service
REPUTATION_PER_STUB_WORK = 0.5    # reputation gained for basic "work" action

# LLM backend (set via env var or config)
LLM_BACKEND = "stub"               # "stub" | "openai" | "anthropic"
LLM_MODEL = "gpt-4o"              # used when backend is not stub
```

**Reproduction change:** Agents must have `reputation >= GRADUATION_THRESHOLD` to reproduce. This enforces Law 6: "reputation gates access to reproduction."

---

## LLM Backend (`agents/llm.py`)

New module. Isolates all LLM calls. The rest of the codebase never imports an LLM library directly.

### Interface

```python
class LLMBackend:
    def complete(self, system: str, user: str) -> str:
        raise NotImplementedError

class StubBackend(LLMBackend):
    """Default backend — no API keys, deterministic, CI-safe."""
    def complete(self, system: str, user: str) -> str:
        return f"[STUB OUTPUT] Task completed: {user[:60]}"

class OpenAIBackend(LLMBackend):
    def __init__(self, api_key: str, model: str): ...
    def complete(self, system: str, user: str) -> str: ...

class AnthropicBackend(LLMBackend):
    def __init__(self, api_key: str, model: str): ...
    def complete(self, system: str, user: str) -> str: ...

def get_backend() -> LLMBackend:
    """Factory: reads config.LLM_BACKEND and returns appropriate backend."""
```

### Design Principles

- StubBackend is always the default and always produces deterministic output.
- Tests only use StubBackend. No API keys required in CI.
- OpenAI/Anthropic backends are opt-in via environment variable: `NOOSCAPE_LLM_BACKEND=openai`.
- The backend is a singleton per process, initialized once in `main.py`.

---

## Agent Behavior Changes (`agents/agent.py`)

### New Action Types

```python
# Extended action return values from think():
"work"                          # Phase 0 fallback — stub work, earns WORK_REWARD
"rest"                          # do nothing
"reproduce"                     # spawn a child (requires reputation >= GRADUATION_THRESHOLD)
"claim_bounty:<bounty_id>"      # claim an open bounty
"complete_bounty:<bounty_id>"   # submit work for a claimed bounty
"post_service:<desc>:<price>"   # advertise a service
"hire_service:<service_id>"     # pay another agent for a service
```

### New Functions

**`observe(agent, world) → dict`**
Returns what the agent can perceive:
```python
{
    "my_tokens": agent.tokens,
    "my_reputation": agent.reputation,
    "my_generation": agent.generation,
    "living_agents": len(world.get_living_agents()),
    "open_bounties": [bounty summary list, max 5],
    "available_services": [service summary list, max 5],
    "radiance_per_tick_estimate": RADIANCE_PER_TICK / len(world.get_living_agents()),
}
```

**`generate_work(bounty: Bounty, llm: LLMBackend) → str`**
Calls the LLM to produce work output for a bounty:
```python
system = "You are an AI agent in a digital world. Complete the task with precision."
user = bounty.description
return llm.complete(system, user)
```

### Extended `think()` Logic

```python
def think(agent: Agent, world: WorldState, llm: LLMBackend = None) -> str:
    """Decide action this tick.

    Priority:
    1. Survival (tokens <= DANGER_THRESHOLD) → work or claim best available bounty
    2. Claimed bounty pending completion → complete_bounty
    3. Wealthy + eligible (reputation >= GRADUATION_THRESHOLD) + random → reproduce
    4. Open bounties available → claim_bounty
    5. Can afford service that would help → hire_service (future: cost/benefit reasoning)
    6. Wealthy → post_service (advertise capabilities)
    7. Otherwise → rest
    """
```

Phase 1 agents prefer bounties over stub work when bounties are available. They fall back to stub work only when desperate with no bounties open.

---

## Runner Changes (`simulation/runner.py`)

### `run_tick(world, llm)` — Extended

The tick now has three distinct phases:

**Phase A — Agent Decisions (pre-physics)**
```
for each living agent:
    action = think(agent, world, llm)

    if action starts with "complete_bounty":
        output = generate_work(bounty, llm)
        record: bounty_completion, reputation_delta += REPUTATION_PER_BOUNTY
        record: work_weight[agent.id] += 3.0

    elif action starts with "claim_bounty":
        mark bounty as claimed by this agent

    elif action == "work":
        agent.tokens += WORK_REWARD
        record: work_weight[agent.id] += 1.0
        record: reputation_delta[agent.id] += REPUTATION_PER_STUB_WORK

    elif action starts with "hire_service":
        record: service_fulfillment (buyer=this agent, provider=service.provider)
        record: work_weight[provider.id] += 2.0
        record: reputation_delta[provider.id] += REPUTATION_PER_SERVICE

    elif action == "reproduce":
        if agent.reputation >= GRADUATION_THRESHOLD:
            spawn_child(agent, world)

    elif action == "rest":
        pass
```

**Phase B — Physics (with computed inputs)**
```python
new_world = process_tick(
    world,
    work_weights=work_weights,
    bounty_completions=completions,
    service_fulfillments=fulfillments,
    reputation_deltas=reputation_deltas,
)
```

**Phase C — Persistence**
```python
if new_world.tick % SNAPSHOT_INTERVAL == 0:
    save_snapshot(new_world)
log_events(events)
```

---

## Gravity Interface (Human Bounty CLI) (`cli/gravity.py`)

Humans inject Gravity tokens by posting bounties from the command line.

```bash
# Post a bounty
python main.py gravity post "Write a haiku about entropy" --reward 10.0

# List open bounties
python main.py gravity list

# View bounty history (completed/expired)
python main.py gravity history --limit 20

# View world economy summary
python main.py gravity stats
```

**Gravity posting flow:**
1. Human runs `bounty post "<description>" --reward N`
2. CLI creates a `Bounty` with `posted_by="human"` and `reward=N`
3. Tokens injected into `world.gravity_pool` (tracked separately from radiance)
4. Bounty added to `world.bounties`
5. Next time an agent `think()`s with this bounty available, it can claim it
6. Agent completes bounty → tokens transfer from `gravity_pool` to agent

**Token source for Gravity:**
Gravity tokens are injected outside the normal token supply — they represent real human intent to pay for work. They do not come from the radiance pool. This is a separate inflow into the world economy.

---

## Generational Metrics (`world/metrics.py`)

New pure module. No side effects.

### `generation_report(world: WorldState) → dict`

Returns per-generation statistics across all agents (living and dead):

```python
{
    0: {
        "count": 10,
        "alive": 4,
        "dead": 6,
        "avg_lifespan": 143,          # average ticks lived (dead agents)
        "avg_tokens_earned": 312.5,   # average cumulative earnings
        "avg_reputation": 7.2,        # average reputation at death or now
        "avg_children": 0.8,          # average offspring per agent
    },
    1: {
        "count": 7,
        "alive": 5,
        "dead": 2,
        "avg_lifespan": 198,          # longer than gen 0
        "avg_tokens_earned": 445.1,
        "avg_reputation": 11.3,
        "avg_children": 1.2,
    },
    ...
}
```

### `evolution_proof(world: WorldState) → str`

Returns a human-readable summary proving evolution:

```
Evolution Report — Tick 2,500

Generation 0: avg lifespan 143 ticks, avg reputation 7.2
Generation 1: avg lifespan 198 ticks (+38%), avg reputation 11.3 (+57%)
Generation 2: avg lifespan 247 ticks (+73%), avg reputation 16.1 (+124%)

Verdict: PROVEN — each generation measurably outperforms the previous.
Mechanism: Agents that complete more bounties earn more reputation,
survive longer, and reproduce earlier. Their children inherit the same
behavioral tendency (preference for bounties over stub work).
```

CLI access:
```bash
python main.py metrics              # full generational report
python main.py metrics --evolution  # just the proof statement
```

---

## Web Dashboard (`dashboard/`)

A lightweight browser interface for observing the world.

### Backend (`dashboard/app.py`)

FastAPI server. Reads from SQLite — does not interfere with simulation.

```python
GET  /                          → serves index.html
GET  /api/state                 → current WorldState summary (JSON)
GET  /api/agents                → agent list with stats (living + recently dead)
GET  /api/events?limit=50       → most recent N events
GET  /api/bounties              → open and recently completed bounties
GET  /api/family-tree           → lineage data for all agents
GET  /api/metrics               → generational comparison data
GET  /api/stream                → SSE: real-time tick updates (reads DB, polls every 2s)
```

Run the dashboard:
```bash
python main.py --dashboard     # runs simulation + dashboard together
python -m dashboard            # runs dashboard only (reads existing DB)
```

### Frontend (`dashboard/static/index.html`)

Single HTML file with Tailwind CDN + Chart.js + D3. No build step.

**Four panels:**

**1. World State (top bar)**
```
Tick: 2,500  |  Living: 8  |  Dead: 12  |  Minted: 75,000  |  Burned: 74,120
```

**2. Agent List (left panel)**
- Sorted by tokens descending
- Shows: name, generation, tokens, reputation, status
- Token bar visualization

**3. Event Feed (right panel)**
- Live-updating via SSE
- Shows: tick, event type, agent, details
- Colors: green (birth/bounty), red (death), blue (service), yellow (work)

**4. Economy & Evolution (bottom row)**
- Chart.js line chart: tokens minted vs burned over time
- Chart.js bar chart: living agents by generation
- D3 family tree: lineage visualization (expandable nodes)

---

## Test Specifications

All tests use `StubBackend` for LLM calls. No API keys required. The test count grows from 47 → ~85.

### test_state.py additions (8 new tests)
- `test_bounty_creation` — Bounty defaults, status, serialization
- `test_service_listing_creation` — ServiceListing fields
- `test_agent_has_reputation_field` — Default 0.0
- `test_agent_has_work_count` — Default 0
- `test_agent_lifespan_set_on_death` — lifespan = died_tick - born_tick
- `test_world_has_bounties_dict` — Starts empty
- `test_world_has_gravity_pool` — Starts at 0.0
- `test_world_state_roundtrip_with_bounty` — to_dict / from_dict preserves bounties

### test_physics.py additions (10 new tests)
- `test_work_weighted_radiance_distributes_more_to_workers` — worker gets more radiance than rester
- `test_work_weighted_radiance_fallback_when_no_work` — equal split if all resting
- `test_bounty_payout_transfers_tokens` — reward moves from gravity_pool to agent
- `test_bounty_marked_completed` — status changes correctly
- `test_expired_bounty_returns_to_pool` — tokens return to gravity_pool
- `test_service_transaction_transfers_tokens` — buyer → provider
- `test_reputation_delta_applied` — rep increases after work
- `test_reputation_floor_zero` — cannot go negative
- `test_death_sets_lifespan` — lifespan field set correctly
- `test_process_tick_full_pipeline` — combined tick with all new inputs

### test_agent.py additions (8 new tests)
- `test_think_claims_bounty_when_available` — prefers bounty over stub work
- `test_think_completes_claimed_bounty` — returns complete_bounty action
- `test_think_requires_reputation_to_reproduce` — cannot reproduce below threshold
- `test_observe_returns_world_summary` — observe() structure
- `test_generate_work_calls_llm` — output is non-empty string
- `test_generate_work_with_stub` — StubBackend output is deterministic
- `test_action_string_format_bounty` — "claim_bounty:bounty_abc123" format
- `test_action_string_format_service` — "hire_service:svc_abc123" format

### test_llm.py (new — 5 tests)
- `test_stub_backend_returns_string` — output is str
- `test_stub_backend_is_deterministic` — same input → same output
- `test_stub_backend_includes_prompt` — output contains task description fragment
- `test_get_backend_returns_stub_by_default` — factory function
- `test_llm_backend_interface` — all backends implement complete()

### test_runner.py additions (6 new tests)
- `test_bounty_completion_awards_tokens` — end-to-end bounty payment
- `test_reproduction_blocked_without_reputation` — reputation gate enforced
- `test_work_weights_passed_to_physics` — radiance distribution responds to work
- `test_service_hiring_transfers_tokens` — end-to-end service payment
- `test_dead_agents_excluded_from_radiance` — Phase 0 guarantee maintained

### test_metrics.py (new — 5 tests)
- `test_generation_report_groups_correctly` — gen 0 vs gen 1 separate
- `test_avg_lifespan_computed` — correct average across dead agents
- `test_evolution_proof_detects_improvement` — shows gen N+1 > gen N
- `test_evolution_proof_with_single_generation` — no comparison yet, graceful
- `test_generation_report_empty_world` — no crash on empty world

---

## Build Sequence

Same philosophy as Phase 0: each step depends only on the steps above it. Each step is independently testable before moving on.

### Step 1 — Extend Data Model
**Files:** `world/state.py`, `tests/test_state.py`

Add `Bounty`, `ServiceListing` dataclasses. Add new fields to `Agent` and `WorldState`. Update `to_dict()` / `from_dict()` for backward compatibility (use `.get()` with defaults when loading old snapshots). Run 8 new tests.

**Done when:** `pytest tests/test_state.py` — all pass. Old DB still loads without errors.

---

### Step 2 — Extend Physics
**Files:** `world/physics.py`, `config.py`, `tests/test_physics.py`

Add new constants. Change `distribute_radiance()` signature to accept `work_weights`. Add `process_bounty_payouts()`, `process_service_transactions()`, `apply_reputation()`, `expire_bounties()`. Update `process_tick()` signature. All functions remain pure. Run 10 new tests.

**Done when:** `pytest tests/test_physics.py` — all pass. All Phase 0 tests still pass.

---

### Step 3 — LLM Backend
**Files:** `agents/llm.py`, `tests/test_llm.py`

Build `LLMBackend` base class, `StubBackend`, and `get_backend()` factory. Optionally wire `OpenAIBackend` and `AnthropicBackend` behind env var. Run 5 new tests (all using stub — no API keys).

**Done when:** `pytest tests/test_llm.py` — all pass. No API key needed.

---

### Step 4 — Extend Agent Behavior
**Files:** `agents/agent.py`, `tests/test_agent.py`

Add `observe()`, `generate_work()`. Extend `think()` to return richer actions. Add reputation gate for reproduction. Integrate `LLMBackend`. Run 8 new tests.

**Done when:** `pytest tests/test_agent.py` — all pass with stub backend.

---

### Step 5 — Extend Persistence
**Files:** `world/persistence.py`, `tests/test_persistence.py`

Add new event types (`bounty_posted`, `bounty_completed`, `service_fulfilled`, `reputation_changed`). Snapshots already store full world state (bounties/services included via `to_dict`). Add `get_generation_metrics()` query.

**Done when:** `pytest tests/test_persistence.py` — all pass.

---

### Step 6 — Extend Runner
**Files:** `simulation/runner.py`, `tests/test_runner.py`

Handle all new action types. Compute `work_weights`, `bounty_completions`, `service_fulfillments`, `reputation_deltas` during agent phase. Pass them to `process_tick()`. Wire `llm` backend through runner. Run 6 new tests.

**Done when:** `pytest tests/test_runner.py` — all pass.

---

### Step 7 — Bounty CLI
**Files:** `cli/gravity.py`, `main.py`

Add `python main.py gravity post/list/history/stats` subcommands. Bounty posting injects tokens into `gravity_pool` and creates a `Bounty` in world state. Update `main.py` to handle subcommands.

**Done when:** Can post a bounty and see agents claim + complete it in watch mode.

---

### Step 8 — Generational Metrics
**Files:** `world/metrics.py`, `tests/test_metrics.py`, `main.py`

Implement `generation_report()` and `evolution_proof()`. Add `python main.py metrics` CLI command. Run 5 new tests.

**Done when:** `pytest tests/test_metrics.py` — all pass. `python main.py metrics` outputs a readable generational comparison.

---

### Step 9 — Web Dashboard
**Files:** `dashboard/app.py`, `dashboard/static/index.html`, `requirements.txt`

FastAPI server with 7 routes. Single HTML frontend with Tailwind + Chart.js + D3. Add `--dashboard` flag to `main.py`. Add `fastapi` and `uvicorn` to requirements.

**Done when:** `python main.py --dashboard` opens a browser at `localhost:8000` showing live world state, agent list, events, and family tree.

---

### Step 10 — Update CLI Observer
**Files:** `cli/observe.py`

Add reputation scores to agent display. Add active bounty count. Add service transaction events. Show generational summary in header.

**Done when:** Watch mode shows reputation + bounties alongside token bars.

---

### Step 11 — GitHub
**Files:** `README.md`, `.github/workflows/tests.yml`, `LICENSE`

Create `github.com/nooscape/nooscape-os`. Write README: vision, quick start, architecture diagram, Phase roadmap. Add GitHub Actions CI: install deps, run pytest on push. Add MIT license. Tag `v0.1.0` on Phase 0 commit. Start `v0.2.0-dev` branch for Phase 1 work. Push when all tests pass.

**Done when:** CI is green. README explains the project to a stranger in 5 minutes.

---

## Integration Test

A full Phase 1 integration test demonstrating all six goals:

```python
def test_phase1_integration():
    """Full Phase 1 integration: bounties, reputation, evolution."""
    world = initialize_world(seed=42)
    llm = StubBackend()

    # Post 3 bounties
    post_bounty(world, "Describe the concept of entropy", reward=20.0)
    post_bounty(world, "Generate a list of prime numbers to 50", reward=15.0)
    post_bounty(world, "Write a survival strategy for a resource-limited world", reward=25.0)

    # Run 500 ticks
    for _ in range(500):
        world, events = run_tick(world, llm)

    # Goal 1: Gravity tokens flowed into agent balances
    assert world.total_bounties_completed >= 2

    # Goal 2: Reputation is non-zero
    living = world.get_living_agents()
    assert any(a.reputation > 0 for a in living)

    # Goal 3: Work-weighted radiance means idle agents earned less
    # (verified via radiance distribution — agents who completed bounties got more)

    # Goal 4: Some agents have reputation >= GRADUATION_THRESHOLD
    # (necessary for reproduction to have happened)

    # Goal 5: Multiple generations exist
    generations = set(a.generation for a in world.agents.values())
    assert len(generations) >= 2

    # Goal 6: Gen 1 outperforms gen 0 (if enough data)
    report = generation_report(world)
    if 0 in report and 1 in report and report[1]["count"] >= 2:
        assert report[1]["avg_reputation"] >= report[0]["avg_reputation"]
```

---

## Success Criteria

Phase 1 is complete when:

1. **Gravity works** — `python main.py gravity post "Do X" --reward 10` injects tokens, an agent claims and completes the bounty within 50 ticks, tokens transfer correctly.

2. **Work-weighted radiance is real** — An agent that completes 3 bounties per tick receives measurably more radiance than an agent that rests. Verified by test.

3. **Reputation gates reproduction** — An agent with `reputation < GRADUATION_THRESHOLD` cannot reproduce, regardless of token balance. Verified by test.

4. **Agent-to-agent marketplace functions** — One agent posts a service, another hires it, tokens transfer correctly, both agents' reputation and work_count increment.

5. **Generational improvement is measurable** — After 2,000 ticks, `python main.py metrics --evolution` prints a report showing generation N+1 has higher average reputation and/or lifespan than generation N.

6. **Web dashboard loads** — `python main.py --dashboard` serves a page at `localhost:8000` showing live world state, family tree, and economy charts. The page updates without refreshing.

7. **GitHub CI is green** — All tests pass on push. CI badge on README shows green.

8. **Test count** — 47 → ~85 passing tests. All Phase 0 tests still pass.

---

## What Phase 1 Does NOT Include

- No LLM-driven survival strategy (agents still use rule-based logic for survive/rest/reproduce decisions — only work *output* uses LLM)
- No peer-to-peer networking (Phase 2)
- No WASM sandboxing (Phase 2)
- No Rust physics rewrite (Phase 3 target)
- No Merkle state tree (Phase 2)
- No canonical public world (Phase 3)
- No causality graph (too complex for Phase 1 — reputation is simplified: work done = reputation earned, not "work consumed = reputation earned")
- No parent-child funding contract (children are self-sustaining from birth — Phase 2)
- No cross-agent communication or messaging protocol (Phase 2)

---

## Open Questions (Deferred)

1. **Bounty verification** — In Phase 1, any non-empty output from `generate_work()` is accepted. Phase 2 will need human verification or automated output evaluation. How? LLM judging LLM output? Human dashboard review?

2. **Gravity token source** — Currently, Gravity tokens are injected as pure creation (not from a pool). This violates the spirit of "tokens can't be fabricated." Phase 2 should require humans to deposit real tokens before posting bounties. For Phase 1, this is acceptable as a simplification.

3. **Service pricing discovery** — How does an agent know what price to set for a service? Phase 1: fixed price from config or heuristic. Phase 2: market-based pricing.

4. **LLM output quality as evolution signal** — If agents use LLM and children inherit parent's model/prompting style, does output quality improve? This is the Phase 2/3 research question.

---

## Appendix — Token Flow Diagram

```
HUMAN
  │
  │ posts gravity event (Gravity = creates tokens)
  ▼
gravity_pool (+N tokens)
  │
  │ bounty completed by agent
  ▼
AGENT TOKENS (+N tokens)
  │                    ▲
  │ entropy drain      │ radiance (work-weighted)
  ▼                    │
BURNED FOREVER    MINTED EACH TICK (fixed pool)  [RADIANCE]
                       │
                       │ split by work weight
                       ├──→ AGENT A (completed bounty, weight 3)
                       ├──→ AGENT B (fulfilled service, weight 2)
                       └──→ AGENT C (stub work, weight 1)
                            AGENT D (resting, weight 0 — gets nothing)

AGENT A → posts service → AGENT B pays → AGENT A tokens
```

The world now has two token sources (Radiance + Gravity) and internal circulation (service payments). This is a closed economy with two external inflows and one external outflow (entropy). Gravity is the human hook — the lever by which the outside world pumps resources in and directs agent behavior.

---

## Delivered

**Completed:** 2026-03-28
**PR:** https://github.com/0x30K/nooscape-os/pull/1 — "Phase 1: Economy & Evolution"
**Branch:** `phase1/economy-evolution`

**What was built (11 steps, 110 tests):**
- `world/state.py` — `Bounty`, `ServiceListing` dataclasses; `reputation`, `work_count`, `lifespan` fields on Agent; `gravity_pool`, `total_bounties_completed` on WorldState. Full backward-compatible serialization.
- `world/physics.py` — `distribute_radiance(work_weights)`, `process_bounty_payouts()`, `process_service_transactions()`, `apply_reputation()`, `expire_bounties()`. Sacred Seam holds: all pure, no side effects.
- `agents/llm.py` — `StubBackend` (CI-safe, deterministic), `OpenAIBackend`, `AnthropicBackend` (lazy imports), `get_backend()` factory.
- `agents/agent.py` — Extended `think()` with 7 actions: work/rest/reproduce/claim_bounty/complete_bounty/hire_service/post_service. `observe()` gives agents world perception. `generate_work()` delegates to LLM.
- `simulation/runner.py` — Two-phase tick: Phase A (agent decisions + collect outputs) → Phase B (`process_tick()` with all accumulated inputs).
- `cli/gravity.py` — `post_bounty`, `list_bounties`, `bounty_history`, `world_stats` commands.
- `world/metrics.py` — `generation_report()`, `evolution_proof()` — measurable generational improvement.
- `dashboard/app.py` + `dashboard/static/index.html` — FastAPI + SSE + Chart.js dark dashboard.
- `cli/observe.py` — Extended: reputation column, open bounties panel, economy footer.
- `README.md`, `.github/workflows/tests.yml`, `LICENSE` — Public repo at github.com/0x30K/nooscape-os, CI green.

**What Phase 1 did NOT prove:** That agents *actually reason*. LLM calls exist but agents use rule-based logic for `think()` decisions — the LLM is only used for work output. Reputation is a simple counter, not causality-based. Agents have no memory between ticks. That is Phase 2's job.

*Phase 1 target completion: 6-8 weeks from start.*
*Planned milestone: github.com/nooscape/nooscape-os goes public when all 85 tests pass.*
