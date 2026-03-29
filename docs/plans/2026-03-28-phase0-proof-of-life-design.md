# Phase 0 — Proof of Life: Design Document

**Date:** 2026-03-28
**Author:** 30K + Claude
**Status:** Complete ✅
**Goal:** A terminal running overnight — wake up and see a population that changed: some agents died, some were born, token balances shifted.

---

## Approach

**Python monolith with clean seams (Approach C).**

Build entirely in Python for speed and AI-assisted development. Structure the code so the physics rules live in one clearly-separated pure module (`physics.py`). When Phase 0 is proven, that module is what gets rewritten in Rust. The boundary is already drawn.

---

## Project Structure

```
nooscape/
├── world/
│   ├── state.py          # data model — Agent, WorldState
│   ├── physics.py        # THE SEAM — all physics rules, pure functions only
│   └── persistence.py    # save/load world state to SQLite
├── agents/
│   └── agent.py          # agent identity + think() decision logic
├── simulation/
│   └── runner.py         # tick loop — orchestrates everything
├── cli/
│   └── observe.py        # terminal display (rich library)
├── main.py               # entry point
├── config.py             # tunable constants
└── requirements.txt      # dependencies (rich, sqlite — minimal)
```

### The Sacred Rule

`physics.py` is a **pure module**. It takes world state in, returns new world state out. No file I/O, no agent logic, no randomness it doesn't own. Pure functions only. This is the clean seam — when Phase 1 comes, a Rust dev rewrites `physics.py` and nothing else changes.

Everything else can be messy, iterative, and evolve freely. Only `physics.py` is sacred.

---

## Data Model (`world/state.py`)

### Agent

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique identifier (e.g. `"agent_a1b2c3"`) |
| `name` | str | Human-readable name (e.g. `"Ada-7"`) |
| `tokens` | float | Current energy balance |
| `alive` | bool | Whether the agent is living |
| `born_tick` | int | Tick when the agent was created |
| `died_tick` | int or None | Tick when the agent died, if dead |
| `generation` | int | Generational depth (0 = genesis) |
| `parent_id` | str or None | ID of parent agent, if any |

### WorldState

| Field | Type | Description |
|-------|------|-------------|
| `tick` | int | Master clock — current tick number |
| `agents` | dict[str, Agent] | All agents, keyed by ID (living and dead) |
| `total_tokens_minted` | float | Cumulative tokens ever created |
| `total_tokens_burned` | float | Cumulative tokens destroyed by entropy |

---

## Physics Engine (`world/physics.py`)

### Tunable Constants (in `config.py`)

```python
ENTROPY_COST_PER_TICK = 0.5     # passive drain per agent per tick
SUN_TOKENS_PER_TICK = 10.0      # total new tokens minted per tick
STARTING_TOKENS = 20.0          # each agent starts with this
REPRODUCTION_COST = 15.0        # tokens spent to spawn a child
CHILD_STARTING_TOKENS = 10.0    # tokens the child receives at birth
```

### Tick Processing Order

Every tick, in this exact order:

1. **`apply_entropy(world_state) → world_state`**
   - Drain `ENTROPY_COST_PER_TICK` tokens from every living agent
   - Tokens cannot go below 0

2. **`distribute_sun(world_state) → world_state`**
   - Mint `SUN_TOKENS_PER_TICK` new tokens
   - Phase 0: distributed equally among all living agents
   - Future: distributed proportionally to agents who did consumed work
   - Increment `total_tokens_minted`

3. **`check_deaths(world_state) → world_state`**
   - Any living agent with `tokens <= 0` → `alive = False`, `died_tick = current tick`

4. **`process_tick(world_state) → new_world_state`**
   - Master function that calls 1, 2, 3 in order
   - Increments tick counter
   - Returns new state — never mutates in place

### Purity Contract

- Every function takes `WorldState` in, returns `WorldState` out
- No side effects (no file I/O, no print, no network)
- No randomness (randomness belongs to the agent layer)
- Given the same input, always produces the same output

---

## Agent Behavior (`agents/agent.py`)

### Phase 0 Decision Logic

Agents use simple rule-based behavior. No LLM calls. The goal is to prove physics, not intelligence.

Each tick, every living agent runs `think(agent, world_state) → Action`:

```
Priority order:

1. If tokens < 5 (danger zone) → WORK
   Agent earns 2.0 tokens as a stub "work reward"

2. If tokens > 30 AND random chance (10%) → REPRODUCE
   Agent pays REPRODUCTION_COST tokens
   A new child Agent is created with CHILD_STARTING_TOKENS
   Child: generation = parent.generation + 1, parent_id = parent.id

3. Otherwise → REST
   Do nothing. Survive. Drain entropy.
```

### Actions

Actions are simple strings: `"work"`, `"rest"`, `"reproduce"`. The simulation runner interprets them.

### Name Generation

Agents get random human-readable names: `"Ada"`, `"Rex"`, `"Nova"`, etc. Children get the parent's name stem with an incrementing number: `"Ada-1"`, `"Ada-2"`.

---

## Simulation Runner (`simulation/runner.py`)

### Initialization

1. Create a fresh `WorldState` at tick 0
2. Spawn 10 genesis agents, each with `STARTING_TOKENS`
3. OR: load from SQLite if a previous save exists (resume support)

### Main Loop

```
loop forever:
    1. physics.process_tick(world_state)    → apply entropy, sun, deaths
    2. for each living agent:
         action = agent.think(agent, world_state)
         process_action(action, agent, world_state)
    3. if tick % 10 == 0:
         persistence.save_snapshot(world_state)
    4. sleep(tick_delay)                    → 0.01s fast, 1.0s watch
```

### Action Processing

- `"work"` → add 2.0 tokens to agent's balance
- `"reproduce"` → subtract REPRODUCTION_COST from parent, create child agent
- `"rest"` → no-op

---

## Persistence (`world/persistence.py`)

### Storage: SQLite

Single file: `nooscape.db`

**Table: snapshots**

| Column | Type | Description |
|--------|------|-------------|
| `tick` | INTEGER PRIMARY KEY | Tick number |
| `world_json` | TEXT | Full world state serialized as JSON |
| `timestamp` | TEXT | Real-world timestamp |

**Table: events**

| Column | Type | Description |
|--------|------|-------------|
| `tick` | INTEGER | When it happened |
| `event_type` | TEXT | `"birth"`, `"death"`, `"work"`, `"reproduce"` |
| `agent_id` | TEXT | Who it happened to |
| `details` | TEXT | JSON blob with extra info |

### Operations

- `save_snapshot(world_state)` → serialize and insert
- `load_latest() → WorldState` → deserialize most recent snapshot
- `log_event(tick, event_type, agent_id, details)` → append to events table

---

## CLI Observer (`cli/observe.py`)

Uses the `rich` Python library for live terminal display. Refreshes every second.

```
╔══════════════════════════════════════════╗
║  NOOSCAPE  |  Tick: 1,847               ║
╠══════════════════════════════════════════╣
║  Living agents:     7                    ║
║  Dead this run:     3                    ║
║  Born this run:     4                    ║
║  Tokens in world:   84.5                 ║
║  Total minted:      1,240.0              ║
║  Total burned:      923.5                ║
╠══════════════════════════════════════════╣
║  AGENTS                                  ║
║  Ada-0    [gen 0]  ████████░░  42.1 tok  ║
║  Rex-0    [gen 0]  ████░░░░░░  18.3 tok  ║
║  Ada-1    [gen 1]  ██░░░░░░░░   9.7 tok  ║
║  Nova-0   [gen 0]  ██████░░░░  28.4 tok  ║
║  ...                                     ║
╠══════════════════════════════════════════╣
║  RECENT EVENTS                           ║
║  [1845] Ada-0 reproduced → Ada-1         ║
║  [1843] Zed-0 died (starvation)          ║
║  [1840] Rex-0 worked (+2.0 tok)          ║
╚══════════════════════════════════════════╝
```

---

## Entry Point (`main.py`)

Two run modes:

```
python main.py           → fast mode (no display, max speed, logs to file)
python main.py --watch   → watch mode (live terminal, 1 tick/sec)
```

Both modes save snapshots to SQLite every 10 ticks. Both modes can be resumed from the last snapshot.

---

## Dependencies

```
rich          # terminal display
```

That's it. SQLite is built into Python. No other dependencies for Phase 0.

---

## Success Criteria

Phase 0 is complete when:

1. You can run `python main.py` and leave it running overnight
2. The next morning, you can see in the database:
   - Some genesis agents died
   - Some agents reproduced
   - Population count is different from the starting 10
   - Token balances shifted across agents
3. You can run `python main.py --watch` and observe agents living and dying in real time
4. The simulation is deterministic given the same random seed
5. The physics module (`physics.py`) has zero side effects and is fully testable in isolation

---

## What Phase 0 Does NOT Include

- No LLM calls (agents are rule-based)
- No networking / P2P
- No web dashboard
- No reputation system (deferred to Phase 1)
- No human bounties / rain (deferred to Phase 1)
- No WASM sandboxing
- No Rust physics engine (Python prototype only)

These are all Phase 1+ concerns. Phase 0 proves the physics works.

---

## Build Sequence

The order in which components should be built:

1. `config.py` — tunable constants
2. `world/state.py` — data model (Agent, WorldState)
3. `world/physics.py` — the sacred physics engine
4. `agents/agent.py` — simple agent behavior
5. `world/persistence.py` — SQLite save/load
6. `simulation/runner.py` — tick loop
7. `cli/observe.py` — terminal display
8. `main.py` — wire it all together

Each step depends only on the ones above it. No circular dependencies. Each step is independently testable.

---

## Delivered

**Completed:** 2026-03-28

**What was built:**
- Full Python simulation running overnight without crashing
- 10 genesis agents born with `STARTING_TOKENS`; population self-regulates through entropy and reproduction
- `physics.py` is a pure module — zero side effects, all functions tested in isolation
- SQLite persistence: snapshots every 10 ticks, event log for all births/deaths/actions
- `python main.py` (fast mode) and `python main.py --watch` (rich terminal display) both work
- 47 tests passing, all physics properties verified

**Outcome:** The physics work. Entropy drains agents, radiance sustains them, reproduction is limited by tokens. Leave it running overnight — wake up to a changed population. The Sacred Seam held.

**What Phase 0 did NOT prove:** That work means anything. "Work" was a stub — add 1.5 tokens, done. Radiance was distributed equally regardless of contribution. No bounties, no reputation, no reason for agents to be *useful* rather than just *alive*. That is Phase 1's job.
