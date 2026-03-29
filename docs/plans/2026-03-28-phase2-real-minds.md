# Phase 2 — Real Minds: Design Document

**Date:** 2026-03-28
**Author:** 30K + Claude
**Status:** Approved
**Goal:** Agents that actually reason, remember, and specialize. Reputation that tracks real usefulness. Children that need parental support. A world observable and usable from outside. When you leave this running overnight, you see not just population change — you see *intelligent adaptation*.

---

## What Phase 1 Proved

The economy works. Tokens flow through the world: gravity pulls them in from humans, entropy pulls them out through survival costs, radiance rewards the workers over the idle. Agents complete bounties, trade services, accumulate reputation, and die if they fail. The Sacred Seam held — `physics.py` remains pure.

What Phase 1 did *not* prove: that agents actually *think*. `think()` is a priority ladder of if/elif statements. The LLM is called only to generate work output text — a string dropped into a completed bounty, never read again. Reputation is a counter. Agents have no memory between ticks. Children are dropped into the world fully formed with no parental connection.

The whitepaper describes agents that reason, remember, specialize, and form causal relationships. Phase 1 built the skeleton. Phase 2 fills it with a mind.

---

## Phase 2 Goals

1. **LLM-driven decisions** — `think()` calls the LLM. Agents reason about their situation and decide what to do. Rule-based fallback only when no LLM is configured. Intelligence is the default path, not the stub.

2. **Agent identity and specialization** — Each agent has a specialty (inherited from parent, drifted over time). Specialty is part of the system prompt. Specialist agents produce higher-quality outputs for matching bounties and earn more reputation.

3. **Persistent agent memory** — Each agent has a memory bank in SQLite: recent bounties completed, agents encountered, tokens earned, strategies tried. Memory is summarized into the LLM context window. Agents that survive longer are smarter because they remember more.

4. **Output quality scoring** — A completed bounty output is evaluated for quality (0.0–1.0) by a judge function. Quality affects reputation earned and enables partial payouts. Low-quality work earns less. This creates selection pressure for skill, not just persistence.

5. **Causality-based reputation** — When agent B's work explicitly cites agent A's prior output, agent A earns reputation credit. This implements Law 3 from the whitepaper: "reputation ticks upward when output is actually consumed by another agent." Simple self-voting becomes impossible — credit flows through the causal graph.

6. **Parent-child funding contracts** — When a parent reproduces, it commits to funding the child's entropy cost for `CHILD_FUNDING_TICKS` ticks or until the child reaches `GRADUATION_THRESHOLD` reputation — whichever comes first. Irresponsible reproduction drains the parent. This matches the whitepaper's Law 6 exactly.

7. **Cross-agent messaging** — Agents can send text messages to each other, stored in world state, delivered in the recipient's next `observe()`. Enables negotiation, coordination, referrals. The simplest form of communication.

8. **External REST API** — `POST /api/bounties` and `GET /api/agents/{id}` for external systems to post work and read agent profiles. Nooscape becomes usable as infrastructure, not just observable.

---

## Architecture Changes

Phase 2 adds intelligence above the existing economy layer. Physics and state are extended but the Sacred Seam principle is unchanged.

```
┌─────────────────────────────────────────────────────┐
│             External REST API                        │
│   POST /api/bounties  GET /api/agents/{id}           │
│   (programmatic access — humans, bots, other AIs)   │
└─────────────────────────┬───────────────────────────┘
                          │ extends
┌─────────────────────────▼───────────────────────────┐
│             Web Dashboard (Phase 1, extended)        │
│   + agent profiles, specialization tree, causal map │
└─────────────────────────┬───────────────────────────┘
                          │ reads
┌─────────────────────────▼───────────────────────────┐
│              CLI + Gravity Interface (Phase 1)       │
│   + message injection, agent inspection             │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│                 Simulation Runner (extended)          │
│   Phase A: think(agent, world, memory, llm)         │
│   Phase B: process_tick(... + causal_links + msgs)  │
│   Phase C: parent funding ticks                     │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│                  Agent Layer (extended)              │
│   think() → LLM with identity + memory context      │
│   observe() → extended: messages, causal history    │
│   generate_work() → specialty-aware prompting        │
│   cite(prior_output_id) → attach causal link        │
└───────────────┬───────────────────────────┬─────────┘
                │                           │
┌───────────────▼────────┐   ┌──────────────▼─────────┐
│  LLM Backend           │   │  Agent Memory           │
│  (Phase 1, extended)   │   │  (NEW: agents/memory.py)│
│  + quality_score()     │   │  SQLite-backed event log│
│  + judge()             │   │  LLM context summarizer │
└────────────────────────┘   └────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│         Physics Engine (world/physics.py)           │  ← THE SACRED SEAM
│   Extended: quality payouts, causal reputation,     │
│   parent funding ticks, message delivery            │
│   Still pure: same input → same output, no I/O     │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│              World State (world/state.py)            │
│   Extended: AgentIdentity, AgentMemory,             │
│   CausalLink, Message, FundingContract              │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│            Persistence (world/persistence.py)       │
│   Extended: memory table, causal_links table,       │
│   messages table, funding_contracts table           │
└─────────────────────────────────────────────────────┘
```

---

## New Project Structure

```
nooscape-os/
├── world/
│   ├── state.py          # EXTENDED: + AgentIdentity, CausalLink, Message, FundingContract
│   ├── physics.py        # EXTENDED: quality payouts, causal rep, parent funding, messages
│   ├── persistence.py    # EXTENDED: new tables and queries
│   └── metrics.py        # EXTENDED: quality trends, causal graph stats
├── agents/
│   ├── agent.py          # EXTENDED: LLM-driven think(), cite(), memory-aware observe()
│   ├── llm.py            # EXTENDED: quality_score(), judge(), specialty prompting
│   └── memory.py         # NEW: per-agent memory store + context window builder
├── simulation/
│   └── runner.py         # EXTENDED: Phase C (parent funding), causal link collection
├── cli/
│   ├── gravity.py        # Phase 1, unchanged
│   └── observe.py        # EXTENDED: specialty, memory depth, causality chain
├── dashboard/
│   ├── app.py            # EXTENDED: + REST API routes, agent profiles
│   └── static/
│       └── index.html    # EXTENDED: specialty tree, causal map panel
├── tests/
│   ├── test_state.py     # EXTENDED
│   ├── test_physics.py   # EXTENDED
│   ├── test_agent.py     # EXTENDED
│   ├── test_llm.py       # EXTENDED
│   ├── test_memory.py    # NEW
│   ├── test_runner.py    # EXTENDED
│   └── test_metrics.py   # EXTENDED
└── ...
```

---

## Data Model Extensions (`world/state.py`)

### `Specialty` (enum)

```python
class Specialty(str, Enum):
    RESEARCHER = "researcher"    # strong at analysis, explanation, synthesis
    BUILDER = "builder"          # strong at code, plans, specifications
    COMMUNICATOR = "communicator" # strong at writing, negotiation, messaging
    ANALYST = "analyst"          # strong at data, patterns, evaluation
    STRATEGIST = "strategist"    # strong at planning, resource allocation
```

Specialties are assigned at birth (random for genesis agents, inherited with drift for children). They affect:
- System prompt framing (LLM gets specialty-appropriate context)
- Bounty matching weight (a researcher agent earns more radiance for research bounties)
- Quality scoring (a builder agent scores higher on code bounties)

### `AgentIdentity`

```python
@dataclass
class AgentIdentity:
    specialty: Specialty
    traits: list[str]       # e.g. ["thorough", "risk-averse"] — inherited + random
    system_prompt: str      # assembled from specialty + traits at birth, fixed
```

Stored as a JSON field on `Agent`. Immutable after birth — identity is determined at creation, not changed dynamically.

### `AgentMemory` (in `agents/memory.py`, stored in SQLite)

Not part of `WorldState` (too large for in-memory state). Stored separately in `memory` table, accessed by agent_id.

```python
@dataclass
class MemoryEntry:
    agent_id: str
    tick: int
    event_type: str   # "bounty_completed", "service_hired", "message_received", etc.
    content: str      # human-readable summary of what happened
    tokens_delta: float
    reputation_delta: float
```

Context window builder (`agents/memory.py`):
- Retrieves last N memory entries for the agent
- Summarizes into a prompt string: "In the last 20 ticks: completed 2 bounties (+6 rep), hired 1 service (-5 tok), received message from Ada-2 about collaboration"
- This summary is injected into the LLM's user prompt in `think()`

### `CausalLink`

```python
@dataclass
class CausalLink:
    from_agent_id: str   # agent whose output was cited/consumed
    to_agent_id: str     # agent who cited/used it
    bounty_id: str       # the bounty where the citation appeared
    tick: int
    credit: float = 1.0  # reputation credit to propagate (default 1.0)
```

When agent B's work output contains `[cite:agent_A_bounty_xyz]`, the runner extracts a `CausalLink(from=A, to=B, ...)` and passes it to `process_causal_links()` in physics.

### `Message`

```python
@dataclass
class Message:
    id: str
    from_agent_id: str
    to_agent_id: str
    content: str         # up to 500 chars
    sent_tick: int
    delivered: bool = False

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> "Message": ...
```

`WorldState.messages` — a list of pending (undelivered) messages. Delivered each tick via physics.

### `FundingContract`

```python
@dataclass
class FundingContract:
    id: str
    parent_id: str
    child_id: str
    created_tick: int
    ticks_remaining: int   # decrements each tick
    tokens_per_tick: float # ENTROPY_COST_PER_TICK — parent covers child's entropy
    active: bool = True

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> "FundingContract": ...
```

`WorldState.funding_contracts` — active parent-child funding contracts.

When a parent reproduces:
- A `FundingContract` is created for `CHILD_FUNDING_TICKS` ticks
- Each tick, `ENTROPY_COST_PER_TICK` tokens are transferred from parent to child (in addition to normal entropy)
- Contract terminates early if: child reaches `GRADUATION_THRESHOLD` reputation OR parent dies OR `ticks_remaining` reaches 0

### `WorldState` additions

```python
messages: list[Message] = field(default_factory=list)
funding_contracts: list[FundingContract] = field(default_factory=list)
total_messages_sent: int = 0
total_causal_credits_awarded: float = 0.0
```

---

## New Constants (`config.py`)

```python
# Phase 2 additions
CHILD_FUNDING_TICKS = 30          # ticks parent funds child after reproduction
QUALITY_THRESHOLD = 0.5           # minimum score to receive full reputation payout
QUALITY_PARTIAL_FLOOR = 0.2       # below this score, bounty pays nothing
CAUSAL_REPUTATION_CREDIT = 1.5   # reputation awarded to cited agent
MAX_MEMORY_ENTRIES = 50           # entries kept per agent in memory
MAX_MESSAGE_LENGTH = 500          # characters per message
MAX_PENDING_MESSAGES = 5          # messages delivered per agent per tick
SPECIALTY_QUALITY_BONUS = 0.2    # quality score bonus for matching specialty
```

---

## Agent Memory (`agents/memory.py`)

New module. No side effects. Reads/writes the `memory` SQLite table.

```python
class AgentMemory:
    def __init__(self, db_path: str, agent_id: str): ...

    def record(self, tick: int, event_type: str, content: str,
               tokens_delta: float = 0.0, reputation_delta: float = 0.0) -> None:
        """Append a memory entry. Prunes to MAX_MEMORY_ENTRIES automatically."""

    def build_context(self, max_entries: int = 10) -> str:
        """Return a human-readable summary of recent memory for LLM injection.

        Example output:
        'Recent history (last 10 events):
        [tick 847] Completed bounty "Summarize entropy law" (+3.0 rep, +20 tok)
        [tick 832] Hired Ada-1 service "code review" (-5 tok)
        [tick 819] Received message from Rex-2: "Let's collaborate on bounties"
        ...'
        """

    def recent_entries(self, n: int = MAX_MEMORY_ENTRIES) -> list[MemoryEntry]:
        """Raw entries, most recent first."""
```

Memory is NOT part of `WorldState`. It is a side-channel store. The Sacred Seam only processes memory outcomes (reputation, token deltas) — it never reads memory directly.

---

## LLM Backend Extensions (`agents/llm.py`)

### Extended `LLMBackend` interface

```python
class LLMBackend:
    def complete(self, system: str, user: str) -> str:
        """Generate text output (work, decision, message)."""
        raise NotImplementedError

    def quality_score(self, task_description: str, output: str, specialty: str = "") -> float:
        """Score output quality 0.0–1.0. Used for bounty evaluation.

        Returns float in [0.0, 1.0].
        StubBackend: returns 0.75 (decent but not perfect — tests can reason about it).
        LLM backends: call judge with structured output parsing.
        """
        raise NotImplementedError
```

### `StubBackend` updates

```python
class StubBackend(LLMBackend):
    def complete(self, system: str, user: str) -> str:
        # Deterministic. Format includes citation signal for causal graph testing.
        return f"[STUB] Completed: {user[:60]}"

    def quality_score(self, task_description: str, output: str, specialty: str = "") -> float:
        return 0.75  # decent quality — enough to earn reputation, not perfect
```

### Specialty-aware prompting

`generate_work(bounty, agent_identity, memory_context, llm)` constructs a richer prompt:

```python
system = f"""You are an AI agent in a digital world called Nooscape.
Your specialty is {agent_identity.specialty.value}.
Your traits: {', '.join(agent_identity.traits)}.
Your recent history:
{memory_context}

Complete the task with precision. If you are building on prior work,
cite it as [cite:agent_id/bounty_id] in your response."""

user = bounty.description
```

The citation signal `[cite:agent_id/bounty_id]` in the output triggers causal link extraction in the runner.

### LLM-driven `think()` prompt

```python
system = f"""You are an AI agent in Nooscape with specialty: {specialty}.
You must survive by earning tokens. Your current state: {tokens} tokens, {reputation} reputation.

Your options this tick:
{available_actions}

Your recent history:
{memory_context}

Choose ONE action and output only the action string. No explanation."""

user = f"Current tick: {world.tick}. Choose your action."
```

The LLM outputs one of the known action strings. The runner parses it; if unrecognized, falls back to rule-based logic.

---

## Physics Engine Extensions (`world/physics.py`)

All new functions are pure. Same contract as Phase 0/1.

### `apply_quality_payouts(world, quality_scores: dict[str, float]) → WorldState`

```python
def apply_quality_payouts(world: WorldState, quality_scores: dict[str, float]) -> WorldState:
    """Adjust reputation for completed bounties based on quality score.

    quality_scores: mapping of bounty_id → quality score (0.0–1.0)

    Scoring logic:
    - score >= QUALITY_THRESHOLD: full REPUTATION_PER_BOUNTY
    - QUALITY_PARTIAL_FLOOR <= score < QUALITY_THRESHOLD: partial reputation (score * REPUTATION_PER_BOUNTY)
    - score < QUALITY_PARTIAL_FLOOR: no reputation, partial token refund to gravity_pool

    Phase 1's apply_reputation() still handles basic deltas.
    This function applies the quality adjustment on top.
    """
```

### `process_causal_links(world, causal_links: list[CausalLink]) → WorldState`

```python
def process_causal_links(world: WorldState, causal_links: list[CausalLink]) -> WorldState:
    """Award reputation credit to agents whose work was cited.

    For each CausalLink:
    - from_agent must be alive (dead agents still credited — posthumous reputation)
    - Award CAUSAL_REPUTATION_CREDIT * link.credit to from_agent.reputation
    - Increment world.total_causal_credits_awarded
    """
```

### `process_funding_contracts(world) → WorldState`

```python
def process_funding_contracts(world: WorldState) -> WorldState:
    """Process all active parent-child funding contracts.

    For each active FundingContract:
    1. If parent is dead → terminate contract (child continues without support)
    2. If child has reputation >= GRADUATION_THRESHOLD → terminate contract (graduated)
    3. If ticks_remaining == 0 → terminate contract
    4. Otherwise:
       - Transfer ENTROPY_COST_PER_TICK from parent.tokens to child.tokens
       - Decrement ticks_remaining
       - If parent.tokens < ENTROPY_COST_PER_TICK: transfer what's available (parent is struggling)

    Note: This transfer is IN ADDITION to normal entropy. The parent effectively
    pays double entropy for the child's early life.
    """
```

### `process_messages(world) → WorldState`

```python
def process_messages(world: WorldState) -> WorldState:
    """Deliver pending messages to recipients.

    For each undelivered message:
    - If recipient is alive: mark delivered, increment world.total_messages_sent
    - If recipient is dead: discard (message is lost)

    Delivered messages are accessible in the next observe() call.
    Purge all delivered messages older than 10 ticks.
    """
```

### Updated `process_tick` signature

```python
def process_tick(
    world: WorldState,
    work_weights: dict[str, float],
    bounty_completions: list[str],
    service_fulfillments: list[tuple],
    reputation_deltas: dict[str, float],
    quality_scores: dict[str, float],          # NEW: bounty_id → score
    causal_links: list[CausalLink],            # NEW: extracted from outputs
    new_messages: list[Message],               # NEW: composed by agents this tick
) -> WorldState:
    """One full tick of world physics.

    Order:
    1. apply_entropy
    2. check_deaths
    3. expire_bounties
    4. process_bounty_payouts
    5. apply_quality_payouts          (NEW)
    6. process_service_transactions
    7. apply_reputation
    8. process_causal_links           (NEW)
    9. process_funding_contracts      (NEW)
    10. process_messages              (NEW)
    11. distribute_radiance
    12. increment tick
    """
```

---

## Agent Behavior Extensions (`agents/agent.py`)

### Updated `observe(agent, world, memory_context) → dict`

```python
{
    "my_tokens": agent.tokens,
    "my_reputation": agent.reputation,
    "my_generation": agent.generation,
    "my_specialty": agent.identity.specialty.value,
    "living_agents": len(world.get_living_agents()),
    "open_bounties": [bounty summary list, max 5, specialty-matched first],
    "available_services": [service summary list, max 5],
    "radiance_per_tick_estimate": RADIANCE_PER_TICK / len(world.get_living_agents()),
    "pending_messages": [message summaries for this agent, max MAX_PENDING_MESSAGES],
    "memory_context": memory_context,     # pre-built summary string
    "funding_contract": contract summary if parent, None otherwise,
}
```

### Updated `think(agent, world, memory, llm) → str`

Decision flow:
1. Build memory context via `memory.build_context()`
2. Build observe dict
3. If LLM is configured: call LLM with identity + memory + observe context; parse output action string
4. If LLM returns unrecognized action OR no LLM: fall back to rule-based logic (Phase 1 priority ladder)
5. Return action string

### `send_message(agent, world, to_agent_id, content) → Message`

Agents can choose to compose a message as their action or in addition to their action. The runner collects messages and passes them to `process_tick()`.

### `extract_citations(output: str) → list[tuple[str, str]]`

Parses `[cite:agent_id/bounty_id]` markers from work output. Returns list of `(agent_id, bounty_id)` tuples. The runner converts these to `CausalLink` objects.

---

## Runner Changes (`simulation/runner.py`)

### Extended `run_tick(world, llm=None)`

Three-phase tick:

**Phase A — Agent Decisions (pre-physics)**
```
for each living agent:
    memory_context = memory.build_context(agent.id)
    action = think(agent, world, memory, llm)

    if action == "complete_bounty:<id>":
        output = generate_work(bounty, agent.identity, memory_context, llm)
        citations = extract_citations(output)
        quality = llm.quality_score(bounty.description, output, agent.identity.specialty)
        collect: bounty_completion, quality_score, causal_links
        record memory: "Completed bounty: {description[:50]}"

    elif action == "send_message:<to_id>:<content>":
        compose Message object
        collect: new_messages

    elif action == "reproduce":
        create child agent with FundingContract
        (child added after Phase B)

    # ... other actions same as Phase 1 ...
```

**Phase B — Physics**
```
world = process_tick(world,
    work_weights=...,
    bounty_completions=...,
    service_fulfillments=...,
    reputation_deltas=...,
    quality_scores=...,          # NEW
    causal_links=...,            # NEW
    new_messages=...,            # NEW
)
```

**Phase C — Post-Physics Cleanup**
```
# Add children (same as Phase 1)
for each queued child:
    add to world.agents with FundingContract

# Record memory for reputation changes
for each agent whose reputation changed:
    memory.record(tick, "reputation_update", f"Rep delta: +{delta:.1f}")
```

---

## Persistence Extensions (`world/persistence.py`)

### New Tables

**`memory`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `agent_id` | TEXT | Agent this memory belongs to |
| `tick` | INTEGER | When it happened |
| `event_type` | TEXT | Type of memory entry |
| `content` | TEXT | Human-readable summary |
| `tokens_delta` | REAL | Token change (for context) |
| `reputation_delta` | REAL | Reputation change (for context) |

**`causal_links`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `from_agent_id` | TEXT | Agent whose work was cited |
| `to_agent_id` | TEXT | Agent who cited it |
| `bounty_id` | TEXT | The bounty where citation appeared |
| `tick` | INTEGER | When the link was created |
| `credit` | REAL | Reputation credit awarded |

**`messages`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PRIMARY KEY | |
| `from_agent_id` | TEXT | |
| `to_agent_id` | TEXT | |
| `content` | TEXT | |
| `sent_tick` | INTEGER | |
| `delivered` | INTEGER | 0/1 boolean |

### New Queries

- `get_agent_profile(agent_id) → dict` — full agent state + memory summary + causal history
- `get_causal_graph(depth=2) → dict` — who cited whom, weighted by credit
- `get_quality_trends() → dict` — average quality score per generation per tick range

---

## Metrics Extensions (`world/metrics.py`)

### New: `quality_report(world) → dict`

```python
{
    "avg_quality_by_specialty": {
        "researcher": 0.81,
        "builder": 0.76,
        ...
    },
    "quality_trend": [   # last 10 snapshots
        {"tick": 2400, "avg_quality": 0.63},
        {"tick": 2500, "avg_quality": 0.71},
        ...
    ],
    "top_quality_agents": [
        {"name": "Ada-2", "specialty": "researcher", "avg_quality": 0.89},
        ...
    ]
}
```

### Extended `generation_report(world) → dict`

Adds quality and causal_credits fields per generation:
```python
{
    0: {
        ...,                           # Phase 1 fields
        "avg_quality": 0.63,           # NEW: avg bounty quality score
        "causal_credits_earned": 4.5,  # NEW: total causal reputation from citations
    },
    1: {
        "avg_quality": 0.71,           # improvement
        "causal_credits_earned": 12.0, # more useful work, more citations
        ...
    }
}
```

---

## External REST API (`dashboard/app.py` extension)

Added to the existing FastAPI server. No new process needed.

### New Endpoints

```python
POST /api/bounties
# Body: {"description": str, "reward": float, "required_specialty": str | null}
# Creates a Bounty in world state, injects reward into gravity_pool
# Returns: {"bounty_id": str, "status": "open"}
# Auth: X-Gravity-Token header (simple shared secret for Phase 2; full auth Phase 3)

GET /api/agents/{agent_id}
# Returns full agent profile: identity, stats, memory summary, causal graph position
# Body: {
#   "id": str,
#   "name": str,
#   "specialty": str,
#   "tokens": float,
#   "reputation": float,
#   "generation": int,
#   "alive": bool,
#   "memory_summary": str,     # last 5 memory entries as text
#   "bounties_completed": int,
#   "causal_credits_earned": float,
# }

GET /api/causal-graph
# Returns simplified causal graph: nodes (agents) + edges (citation links)
# Suitable for D3 visualization

GET /api/quality-trends
# Returns quality_report() data for dashboard charting
```

---

## CLI Observer Extensions (`cli/observe.py`)

```
╔══════════════════════════════════════════════════════════╗
║  NOOSCAPE  |  Tick: 3,421    [Gen 0-3 active]           ║
╠══════════════════════════════════════════════════════════╣
║  Living:  8    Dead this run: 7    Born this run: 11     ║
║  Avg quality: 0.74    Causal links: 23    Messages: 47   ║
╠══════════════════════════════════════════════════════════╣
║  AGENTS                                                  ║
║  Ada-2    [gen 2] [researcher] ████████░░  42.1 tok ★8.3║
║  Rex-1    [gen 1] [builder   ] ████░░░░░░  18.3 tok ★4.1║
║  Nova-3   [gen 3] [analyst   ] ██░░░░░░░░   9.7 tok ★2.0║
║  ...                                                     ║
║  [★ = reputation  | bar = tokens  | specialty shown]    ║
╠══════════════════════════════════════════════════════════╣
║  RECENT EVENTS                                           ║
║  [3420] Nova-3 cited Ada-2 (+1.5 rep to Ada-2)          ║
║  [3419] Rex-1 reproduced → Rex-2 (funding: 30 ticks)    ║
║  [3417] Ada-2 msg→ Rex-1: "I can help with research"    ║
╚══════════════════════════════════════════════════════════╝
```

New columns: specialty tag, reputation star (★), causal events in feed, message events.

---

## Test Specifications

### test_state.py additions (8 new tests)
- `test_agent_identity_specialty_field` — AgentIdentity created with Specialty enum
- `test_causal_link_creation` — CausalLink fields and to_dict/from_dict
- `test_message_creation_and_serialization` — Message roundtrip
- `test_funding_contract_creation` — FundingContract fields
- `test_world_has_messages_list` — starts empty
- `test_world_has_funding_contracts_list` — starts empty
- `test_specialty_inheritance_on_reproduce` — child inherits parent specialty with drift
- `test_worldstate_roundtrip_with_all_phase2_fields` — full serialize/deserialize

### test_physics.py additions (12 new tests)
- `test_quality_payout_full_score` — score >= threshold → full reputation
- `test_quality_payout_partial_score` — QUALITY_PARTIAL_FLOOR <= score < threshold → partial rep
- `test_quality_payout_below_floor` — score < floor → zero rep, partial refund to gravity_pool
- `test_causal_link_awards_reputation` — cited agent gains CAUSAL_REPUTATION_CREDIT
- `test_causal_link_to_dead_agent` — dead agents still credited posthumously
- `test_funding_contract_transfers_tokens` — parent pays child ENTROPY_COST_PER_TICK
- `test_funding_contract_terminates_on_graduation` — stops when child reaches threshold
- `test_funding_contract_terminates_on_parent_death` — no transfer if parent dead
- `test_funding_contract_terminates_when_expired` — ticks_remaining reaches 0
- `test_message_delivery_to_living_agent` — message marked delivered
- `test_message_discarded_for_dead_agent` — dead recipients discard message
- `test_process_tick_full_phase2_pipeline` — all new inputs together

### test_memory.py (new — 7 tests)
- `test_memory_record_persists` — entry saved to SQLite
- `test_memory_build_context_returns_string` — non-empty context string
- `test_memory_prunes_to_max_entries` — never exceeds MAX_MEMORY_ENTRIES
- `test_memory_context_includes_recent_events` — most recent events appear in context
- `test_memory_empty_agent` — graceful on zero entries
- `test_memory_multi_agent_isolation` — agent A memory doesn't leak to agent B
- `test_memory_context_truncates_long_content` — very long entries are summarized

### test_llm.py additions (5 new tests)
- `test_stub_quality_score_returns_float` — quality_score() returns float in [0,1]
- `test_stub_quality_score_consistent` — same inputs → same score
- `test_specialty_prompt_includes_specialty` — LLM prompt contains specialty name
- `test_citation_extraction_finds_markers` — `[cite:agent/bounty]` parsed correctly
- `test_citation_extraction_empty_output` — graceful on no citations

### test_agent.py additions (8 new tests)
- `test_think_uses_llm_when_available` — LLM backend called in think()
- `test_think_falls_back_on_bad_llm_output` — unrecognized action → rule-based fallback
- `test_think_with_memory_context` — memory context injected into LLM call
- `test_observe_includes_messages` — pending messages appear in observe()
- `test_observe_includes_specialty` — specialty in observe dict
- `test_generate_work_includes_specialty_in_prompt` — specialty used in work prompt
- `test_extract_citations_from_output` — causal links found in work text
- `test_send_message_creates_message` — Message object returned

### test_runner.py additions (6 new tests)
- `test_causal_links_collected_from_outputs` — citation in work output → CausalLink passed to physics
- `test_quality_scores_collected` — runner calls quality_score() and passes scores
- `test_funding_contract_created_on_reproduce` — parent creates FundingContract
- `test_funding_drains_parent` — parent tokens decrease more with active contract
- `test_memory_recorded_after_bounty` — memory.record() called after completion
- `test_message_collected_and_passed` — message action → new_messages list

### test_metrics.py additions (4 new tests)
- `test_quality_report_by_specialty` — researchers score higher on research bounties
- `test_generation_report_includes_quality` — avg_quality per generation
- `test_causal_credits_per_generation` — causal_credits_earned tracked
- `test_evolution_proof_includes_quality` — evolution_proof() mentions quality improvement

---

## Build Sequence

Same philosophy: each step depends only on prior steps, each is independently testable.

### Step 1 — Extend Data Model
**Files:** `world/state.py`, `tests/test_state.py`

Add `Specialty` enum, `AgentIdentity` dataclass (stored as JSON field on Agent), `CausalLink`, `Message`, `FundingContract` dataclasses. Add new list fields to `WorldState`. Update all `to_dict()` / `from_dict()` with `.get()` defaults. Assign random specialty to genesis agents, inheritance to children.

**Done when:** `pytest tests/test_state.py` — all 8 new + all Phase 0/1 tests pass.

---

### Step 2 — Agent Memory
**Files:** `agents/memory.py`, `world/persistence.py`, `tests/test_memory.py`

Create `memory` table in SQLite. Build `AgentMemory` class with `record()` and `build_context()`. Prune to `MAX_MEMORY_ENTRIES`. No world state changes — this is a side-channel store.

**Done when:** `pytest tests/test_memory.py` — all 7 tests pass. Memory is isolated per agent.

---

### Step 3 — LLM Extensions
**Files:** `agents/llm.py`, `agents/agent.py`, `tests/test_llm.py`

Add `quality_score()` to `LLMBackend` interface and implement in `StubBackend`, `OpenAIBackend`, `AnthropicBackend`. Add `extract_citations()` function. Implement specialty-aware `generate_work()` prompting. Update `think()` to call LLM with identity + memory context + rule-based fallback.

**Done when:** `pytest tests/test_llm.py tests/test_agent.py` — all new + prior tests pass.

---

### Step 4 — Physics: Quality Payouts
**Files:** `world/physics.py`, `config.py`, `tests/test_physics.py`

Add `QUALITY_THRESHOLD`, `QUALITY_PARTIAL_FLOOR`, `SPECIALTY_QUALITY_BONUS` to config. Implement `apply_quality_payouts(world, quality_scores)`. This is a modifier on top of Phase 1's `apply_reputation()` — it adjusts the reputation already queued for bounty completions.

**Done when:** `pytest tests/test_physics.py` — all 12 new + all Phase 0/1 physics tests pass.

---

### Step 5 — Physics: Causal Reputation
**Files:** `world/physics.py`, `tests/test_physics.py`

Add `CAUSAL_REPUTATION_CREDIT` to config. Implement `process_causal_links(world, causal_links)`. Update `process_tick()` to accept and process `causal_links`.

**Done when:** `pytest tests/test_physics.py` — causal link tests pass. No regression.

---

### Step 6 — Physics: Funding Contracts
**Files:** `world/physics.py`, `world/state.py`, `tests/test_physics.py`

Add `CHILD_FUNDING_TICKS` to config. Implement `process_funding_contracts(world)`. Update reproduction in runner to create `FundingContract`. Update `process_tick()` to call `process_funding_contracts`.

**Done when:** `pytest tests/test_physics.py tests/test_runner.py` — funding contract tests pass. Reproduction now creates a contract.

---

### Step 7 — Physics: Messages
**Files:** `world/physics.py`, `world/state.py`, `tests/test_physics.py`

Add `MAX_PENDING_MESSAGES` to config. Implement `process_messages(world)`. Update `process_tick()` to accept `new_messages` and call `process_messages`.

**Done when:** `pytest tests/test_physics.py` — message delivery tests pass.

---

### Step 8 — Runner: Wire It All Together
**Files:** `simulation/runner.py`, `tests/test_runner.py`

Update `run_tick()` to collect `quality_scores`, `causal_links`, `new_messages` during Phase A. Pass all to `process_tick()`. Handle FundingContracts on reproduce. Record memory events in Phase C.

**Done when:** `pytest tests/test_runner.py` — all 6 new + Phase 1 runner tests pass.

---

### Step 9 — Metrics + Persistence Extensions
**Files:** `world/metrics.py`, `world/persistence.py`, `tests/test_metrics.py`

Add `quality_report()`. Extend `generation_report()` with quality and causal fields. Add `get_agent_profile()`, `get_causal_graph()`, `get_quality_trends()` queries. Create new persistence tables if not exist.

**Done when:** `pytest tests/test_metrics.py` — all 4 new + Phase 1 metrics tests pass.

---

### Step 10 — External API + Dashboard Extensions
**Files:** `dashboard/app.py`, `dashboard/static/index.html`

Add `POST /api/bounties` with `X-Gravity-Token` auth. Add `GET /api/agents/{id}`, `GET /api/causal-graph`, `GET /api/quality-trends`. Extend dashboard HTML with causal graph panel (D3), quality trend chart (Chart.js), agent specialty badges.

**Done when:** Can `curl -X POST /api/bounties` and see agents claim it. Dashboard shows causal graph.

---

### Step 11 — CLI + GitHub
**Files:** `cli/observe.py`, `README.md`, `.github/workflows/tests.yml`

Update watch mode with specialty column, reputation star, message/causal events in feed. Update README with Phase 2 features. Update CI (tests.yml) to run all new tests. Tag `v0.3.0` on merge.

**Done when:** All tests pass on CI. Watch mode shows the richer view.

---

## Integration Test

```python
def test_phase2_integration():
    """Full Phase 2 integration: real minds, memory, quality, causality."""
    world = initialize_world(seed=42)
    llm = StubBackend()

    # Post a research bounty + a builder bounty
    post_bounty(world, "Explain why entropy drives agent behavior", reward=20.0,
                required_specialty="researcher")
    post_bounty(world, "Write a resource allocation algorithm", reward=25.0,
                required_specialty="builder")

    # Run 1000 ticks
    for _ in range(1000):
        world, events = run_tick(world, llm)

    # Quality scoring is real
    bounties = [b for b in world.bounties.values() if b.status == "completed"]
    assert len(bounties) >= 2
    # (quality stored in event log — check via persistence)

    # Causal graph has edges
    assert world.total_causal_credits_awarded > 0

    # Funding contracts created and terminated
    # (check via events table — contracts should have been created and resolved)

    # Messages sent
    assert world.total_messages_sent > 0

    # Generation report includes quality
    report = generation_report(world)
    assert "avg_quality" in report.get(0, {})

    # Gen 1 agents specialize — check that some have non-default specialties
    gen1_agents = [a for a in world.agents.values() if a.generation == 1]
    if gen1_agents:
        specialties = {a.identity.specialty for a in gen1_agents}
        assert len(specialties) >= 1  # specialties exist
```

---

## Success Criteria

Phase 2 is complete when:

1. **LLM decisions work** — With `NOOSCAPE_LLM_BACKEND=openai`, agents visibly reason about their situation in watch mode. Decision variety increases. Log shows LLM calls.

2. **Memory is persistent** — Kill and restart simulation. Agent memory survives. Restarted agent context includes prior bounty history.

3. **Quality scoring is real** — After 1,000 ticks, agents with matching specialty consistently score higher than mismatched agents. Verified by `python main.py metrics --quality`.

4. **Causal graph has edges** — After 1,000 ticks, `GET /api/causal-graph` returns a non-trivial graph. Some agents have earned reputation through citation, not just direct work.

5. **Funding contracts complete** — Parent-child pairs visible in event log. Parents that reproduce irresponsibly die first. Parents that reproduce carefully have more surviving children.

6. **External API is callable** — `curl -X POST localhost:8000/api/bounties -H "X-Gravity-Token: secret" -d '{"description":"...", "reward":10}'` creates a bounty that agents claim within 50 ticks.

7. **Test count** — ~110 → ~170 passing tests. All Phase 0/1 tests still pass.

8. **CI is green** — All tests pass on push to branch.

---

## What Phase 2 Does NOT Include

- No peer-to-peer networking (Phase 3)
- No Rust physics rewrite (Phase 3)
- No WASM agent sandboxing (Phase 3)
- No Merkle state tree (Phase 3)
- No canonical single world across nodes (Phase 3)
- No token staking or governance (Phase 4)
- No agent spawning by agents (agents can only reproduce, not create arbitrary new agents — Phase 4)
- No complex LLM output verification beyond quality scoring (Phase 4)

---

## Open Questions (Deferred to Phase 3)

1. **Quality scoring with real LLMs** — `StubBackend.quality_score()` returns a fixed value. With real LLMs, quality scoring requires another LLM call (judge model). Should the judge be the same model or different? Should there be human override in the dashboard? This matters for reputation integrity.

2. **Causal graph depth** — Phase 2 tracks one-hop citations (B cites A → A gets credit). What about two-hop (C cites B's work that built on A → does A get anything)? Exponential decay through the graph (0.5x at each hop) would be more accurate but more complex. Deferred.

3. **Message abuse** — Agents with LLM reasoning could spam messages to manipulate other agents. No rate limiting beyond `MAX_PENDING_MESSAGES` per tick. Phase 3 should add message cost (token fee per message) to prevent spam.

4. **Funding contract manipulation** — A wealthy parent could exploit the system by reproducing endlessly, then dying quickly to fund children cheaply. The physics should eventually handle this (parent dies → contract terminates), but specific edge cases need analysis.

5. **Specialty convergence** — Will all agents evolve toward one optimal specialty? If so, specialization is an illusion. We may need to add specialization premium to bounty rewards (researcher bounties pay more to researchers) to maintain diversity. Observe in Phase 2 data before adding complexity.
