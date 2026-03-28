# Phase 0 — Proof of Life: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single-node Python simulation where agents are born, live, earn tokens, drain entropy, reproduce, and die — leave it running overnight and wake up to a changed population.

**Architecture:** Python monolith with clean seams. All physics rules live in one pure module (`world/physics.py`) that takes state in and returns new state out — no side effects. This module is the future Rust rewrite target. Everything else (agents, persistence, CLI) calls into it.

**Tech Stack:** Python 3.10+, SQLite (built-in), rich (terminal display)

---

## File Map

| File | Responsibility | Created in Task |
|------|---------------|-----------------|
| `config.py` | All tunable constants | Task 1 |
| `world/__init__.py` | Package init | Task 1 |
| `world/state.py` | Agent and WorldState dataclasses | Task 2 |
| `world/physics.py` | Pure physics functions (THE SEAM) | Task 3 |
| `agents/__init__.py` | Package init | Task 1 |
| `agents/agent.py` | Agent think() logic and name generation | Task 4 |
| `world/persistence.py` | SQLite save/load/events | Task 5 |
| `simulation/__init__.py` | Package init | Task 1 |
| `simulation/runner.py` | Tick loop orchestration | Task 6 |
| `cli/__init__.py` | Package init | Task 1 |
| `cli/observe.py` | Rich terminal display | Task 7 |
| `main.py` | Entry point with --watch flag | Task 8 |
| `requirements.txt` | Dependencies | Task 1 |
| `tests/test_state.py` | State model tests | Task 2 |
| `tests/test_physics.py` | Physics engine tests | Task 3 |
| `tests/test_agent.py` | Agent behavior tests | Task 4 |
| `tests/test_persistence.py` | SQLite tests | Task 5 |
| `tests/test_runner.py` | Runner integration tests | Task 6 |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `config.py`
- Create: `requirements.txt`
- Create: `world/__init__.py`, `agents/__init__.py`, `simulation/__init__.py`, `cli/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
mkdir world agents simulation cli tests
```

- [ ] **Step 2: Create package init files**

Create empty `__init__.py` in each package:

`world/__init__.py`:
```python
```

`agents/__init__.py`:
```python
```

`simulation/__init__.py`:
```python
```

`cli/__init__.py`:
```python
```

`tests/__init__.py`:
```python
```

- [ ] **Step 3: Create config.py**

`config.py`:
```python
"""Nooscape — tunable constants for the world physics."""

# Physics
ENTROPY_COST_PER_TICK = 0.5       # tokens drained per agent per tick
SUN_TOKENS_PER_TICK = 10.0        # total new tokens minted per tick

# Agents
STARTING_TOKENS = 20.0            # tokens each genesis agent starts with
WORK_REWARD = 2.0                 # tokens earned when an agent works
DANGER_THRESHOLD = 5.0            # below this, agent will always work
REPRODUCE_THRESHOLD = 30.0        # above this, agent may reproduce
REPRODUCE_CHANCE = 0.10           # 10% chance to reproduce when above threshold

# Reproduction
REPRODUCTION_COST = 15.0          # tokens parent spends to reproduce
CHILD_STARTING_TOKENS = 10.0      # tokens the child starts with

# Simulation
GENESIS_AGENT_COUNT = 10          # number of agents at world creation
SNAPSHOT_INTERVAL = 10            # save to SQLite every N ticks
FAST_TICK_DELAY = 0.01            # seconds between ticks in fast mode
WATCH_TICK_DELAY = 1.0            # seconds between ticks in watch mode
```

- [ ] **Step 4: Create requirements.txt**

`requirements.txt`:
```
rich>=13.0
pytest>=8.0
```

- [ ] **Step 5: Install dependencies**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
pip install -r requirements.txt
```

- [ ] **Step 6: Initialize git repo and commit**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
git init
git add config.py requirements.txt world/__init__.py agents/__init__.py simulation/__init__.py cli/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure and config"
```

---

### Task 2: World State Data Model

**Files:**
- Create: `world/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing tests for Agent and WorldState**

`tests/test_state.py`:
```python
"""Tests for the world state data model."""
import pytest
from world.state import Agent, WorldState, create_agent, create_world


class TestAgent:
    def test_create_agent_defaults(self):
        agent = create_agent(agent_id="agent_001", name="Ada-0", tokens=20.0)
        assert agent.id == "agent_001"
        assert agent.name == "Ada-0"
        assert agent.tokens == 20.0
        assert agent.alive is True
        assert agent.born_tick == 0
        assert agent.died_tick is None
        assert agent.generation == 0
        assert agent.parent_id is None

    def test_create_agent_with_parent(self):
        agent = create_agent(
            agent_id="agent_002",
            name="Ada-1",
            tokens=10.0,
            born_tick=50,
            generation=1,
            parent_id="agent_001",
        )
        assert agent.generation == 1
        assert agent.parent_id == "agent_001"
        assert agent.born_tick == 50


class TestWorldState:
    def test_create_world_empty(self):
        world = create_world()
        assert world.tick == 0
        assert world.agents == {}
        assert world.total_tokens_minted == 0.0
        assert world.total_tokens_burned == 0.0

    def test_add_agent_to_world(self):
        world = create_world()
        agent = create_agent(agent_id="agent_001", name="Ada-0", tokens=20.0)
        world.agents[agent.id] = agent
        assert len(world.agents) == 1
        assert world.agents["agent_001"].name == "Ada-0"

    def test_get_living_agents(self):
        world = create_world()
        alive = create_agent(agent_id="a1", name="Ada-0", tokens=20.0)
        dead = create_agent(agent_id="a2", name="Rex-0", tokens=0.0)
        dead.alive = False
        world.agents["a1"] = alive
        world.agents["a2"] = dead
        living = world.get_living_agents()
        assert len(living) == 1
        assert living[0].id == "a1"

    def test_agent_to_dict_roundtrip(self):
        agent = create_agent(
            agent_id="agent_001", name="Ada-0", tokens=20.0,
            born_tick=5, generation=1, parent_id="agent_000",
        )
        d = agent.to_dict()
        restored = Agent.from_dict(d)
        assert restored.id == agent.id
        assert restored.name == agent.name
        assert restored.tokens == agent.tokens
        assert restored.generation == agent.generation
        assert restored.parent_id == agent.parent_id

    def test_world_to_dict_roundtrip(self):
        world = create_world()
        agent = create_agent(agent_id="a1", name="Ada-0", tokens=20.0)
        world.agents["a1"] = agent
        world.tick = 42
        world.total_tokens_minted = 100.0
        d = world.to_dict()
        restored = WorldState.from_dict(d)
        assert restored.tick == 42
        assert restored.total_tokens_minted == 100.0
        assert "a1" in restored.agents
        assert restored.agents["a1"].name == "Ada-0"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/test_state.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'world.state'`

- [ ] **Step 3: Implement state.py**

`world/state.py`:
```python
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
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Agent":
        return cls(
            id=d["id"],
            name=d["name"],
            tokens=d["tokens"],
            alive=d["alive"],
            born_tick=d["born_tick"],
            died_tick=d.get("died_tick"),
            generation=d["generation"],
            parent_id=d.get("parent_id"),
        )


@dataclass
class WorldState:
    """The complete state of the world at a given tick."""
    tick: int = 0
    agents: dict = field(default_factory=dict)  # dict[str, Agent]
    total_tokens_minted: float = 0.0
    total_tokens_burned: float = 0.0

    def get_living_agents(self) -> list:
        """Return a list of all living agents."""
        return [a for a in self.agents.values() if a.alive]

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "agents": {aid: a.to_dict() for aid, a in self.agents.items()},
            "total_tokens_minted": self.total_tokens_minted,
            "total_tokens_burned": self.total_tokens_burned,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorldState":
        agents = {aid: Agent.from_dict(ad) for aid, ad in d["agents"].items()}
        return cls(
            tick=d["tick"],
            agents=agents,
            total_tokens_minted=d["total_tokens_minted"],
            total_tokens_burned=d["total_tokens_burned"],
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/test_state.py -v
```
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add world/state.py tests/test_state.py
git commit -m "feat: add Agent and WorldState data model with serialization"
```

---

### Task 3: Physics Engine (The Sacred Seam)

**Files:**
- Create: `world/physics.py`
- Create: `tests/test_physics.py`

- [ ] **Step 1: Write failing tests for entropy**

`tests/test_physics.py`:
```python
"""Tests for the physics engine — the sacred seam.

Every test verifies purity: same input → same output, no side effects.
"""
import pytest
from world.state import create_agent, create_world, WorldState
from world.physics import apply_entropy, distribute_sun, check_deaths, process_tick
import config


class TestApplyEntropy:
    def test_drains_tokens_from_living_agents(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)
        world.agents["a2"] = create_agent("a2", "Rex-0", tokens=10.0)

        new_world = apply_entropy(world)

        assert new_world.agents["a1"].tokens == 20.0 - config.ENTROPY_COST_PER_TICK
        assert new_world.agents["a2"].tokens == 10.0 - config.ENTROPY_COST_PER_TICK

    def test_tokens_cannot_go_below_zero(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=0.1)

        new_world = apply_entropy(world)

        assert new_world.agents["a1"].tokens == 0.0

    def test_does_not_drain_dead_agents(self):
        world = create_world()
        dead = create_agent("a1", "Ada-0", tokens=5.0)
        dead.alive = False
        world.agents["a1"] = dead

        new_world = apply_entropy(world)

        assert new_world.agents["a1"].tokens == 5.0

    def test_tracks_total_burned(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)
        world.agents["a2"] = create_agent("a2", "Rex-0", tokens=20.0)

        new_world = apply_entropy(world)

        assert new_world.total_tokens_burned == config.ENTROPY_COST_PER_TICK * 2

    def test_does_not_mutate_original(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)
        original_tokens = world.agents["a1"].tokens

        apply_entropy(world)

        assert world.agents["a1"].tokens == original_tokens


class TestDistributeSun:
    def test_distributes_equally_among_living(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)
        world.agents["a2"] = create_agent("a2", "Rex-0", tokens=10.0)

        new_world = distribute_sun(world)

        expected_each = config.SUN_TOKENS_PER_TICK / 2
        assert new_world.agents["a1"].tokens == 10.0 + expected_each
        assert new_world.agents["a2"].tokens == 10.0 + expected_each

    def test_tracks_total_minted(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)

        new_world = distribute_sun(world)

        assert new_world.total_tokens_minted == config.SUN_TOKENS_PER_TICK

    def test_no_agents_no_distribution(self):
        world = create_world()

        new_world = distribute_sun(world)

        assert new_world.total_tokens_minted == 0.0

    def test_skips_dead_agents(self):
        world = create_world()
        alive = create_agent("a1", "Ada-0", tokens=10.0)
        dead = create_agent("a2", "Rex-0", tokens=5.0)
        dead.alive = False
        world.agents["a1"] = alive
        world.agents["a2"] = dead

        new_world = distribute_sun(world)

        assert new_world.agents["a1"].tokens == 10.0 + config.SUN_TOKENS_PER_TICK
        assert new_world.agents["a2"].tokens == 5.0

    def test_does_not_mutate_original(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=10.0)

        distribute_sun(world)

        assert world.agents["a1"].tokens == 10.0


class TestCheckDeaths:
    def test_kills_agent_at_zero_tokens(self):
        world = create_world()
        world.tick = 42
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=0.0)

        new_world = check_deaths(world)

        assert new_world.agents["a1"].alive is False
        assert new_world.agents["a1"].died_tick == 42

    def test_does_not_kill_agent_with_tokens(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=0.1)

        new_world = check_deaths(world)

        assert new_world.agents["a1"].alive is True
        assert new_world.agents["a1"].died_tick is None

    def test_does_not_mutate_original(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=0.0)

        check_deaths(world)

        assert world.agents["a1"].alive is True


class TestProcessTick:
    def test_increments_tick(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)

        new_world = process_tick(world)

        assert new_world.tick == 1

    def test_applies_entropy_then_sun_then_deaths(self):
        """An agent with exactly ENTROPY_COST tokens should die after entropy
        but the sun might save them if there are few enough agents."""
        world = create_world()
        # Agent has exactly entropy cost — after drain it's 0, but sun adds tokens
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=config.ENTROPY_COST_PER_TICK)

        new_world = process_tick(world)

        # Entropy drains to 0, sun adds SUN_TOKENS_PER_TICK (only 1 agent gets it all)
        # Then death check: agent has SUN_TOKENS_PER_TICK, so survives
        assert new_world.agents["a1"].alive is True
        assert new_world.agents["a1"].tokens == config.SUN_TOKENS_PER_TICK

    def test_agent_dies_when_sun_not_enough(self):
        """With many agents, sun per agent may not cover entropy."""
        world = create_world()
        # Create 100 agents each with barely enough tokens
        for i in range(100):
            world.agents[f"a{i}"] = create_agent(
                f"a{i}", f"Agent-{i}", tokens=0.01
            )

        new_world = process_tick(world)

        # Each gets entropy drained (0.01 - 0.5 = 0, clamped)
        # Sun per agent = 10.0 / 100 = 0.1
        # So each agent has 0.1 tokens — alive
        living = new_world.get_living_agents()
        assert len(living) == 100

    def test_does_not_mutate_original(self):
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)

        process_tick(world)

        assert world.tick == 0
        assert world.agents["a1"].tokens == 20.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/test_physics.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'world.physics'`

- [ ] **Step 3: Implement physics.py**

`world/physics.py`:
```python
"""Nooscape physics engine — THE SACRED SEAM.

RULES:
  1. Every function takes WorldState in, returns NEW WorldState out.
  2. No side effects. No file I/O. No print. No network.
  3. No randomness. Randomness belongs to the agent layer.
  4. Given the same input, always produces the same output.

This module is the future Rust rewrite target.
When that day comes, only this file changes.
"""
import copy
from world.state import WorldState
import config


def apply_entropy(world: WorldState) -> WorldState:
    """Drain ENTROPY_COST_PER_TICK tokens from every living agent.

    Tokens cannot go below zero. Dead agents are not drained.
    Increments total_tokens_burned by the amount actually drained.
    """
    new_world = copy.deepcopy(world)
    total_burned = 0.0

    for agent in new_world.agents.values():
        if not agent.alive:
            continue
        drain = min(agent.tokens, config.ENTROPY_COST_PER_TICK)
        agent.tokens -= drain
        total_burned += drain

    new_world.total_tokens_burned += total_burned
    return new_world


def distribute_sun(world: WorldState) -> WorldState:
    """Mint SUN_TOKENS_PER_TICK and distribute equally among living agents.

    If there are no living agents, nothing is minted.
    Increments total_tokens_minted.
    """
    new_world = copy.deepcopy(world)
    living = [a for a in new_world.agents.values() if a.alive]

    if not living:
        return new_world

    share = config.SUN_TOKENS_PER_TICK / len(living)
    for agent in living:
        agent.tokens += share

    new_world.total_tokens_minted += config.SUN_TOKENS_PER_TICK
    return new_world


def check_deaths(world: WorldState) -> WorldState:
    """Kill any living agent whose tokens have reached zero.

    Sets alive=False and records died_tick.
    """
    new_world = copy.deepcopy(world)

    for agent in new_world.agents.values():
        if agent.alive and agent.tokens <= 0:
            agent.alive = False
            agent.died_tick = new_world.tick

    return new_world


def process_tick(world: WorldState) -> WorldState:
    """Process one full tick of world physics.

    Order: entropy → sun → deaths → increment tick.
    Returns a new WorldState. Never mutates the input.
    """
    new_world = apply_entropy(world)
    new_world = distribute_sun(new_world)
    new_world = check_deaths(new_world)
    new_world.tick = world.tick + 1
    return new_world
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/test_physics.py -v
```
Expected: All 15 tests PASS

- [ ] **Step 5: Commit**

```bash
git add world/physics.py tests/test_physics.py
git commit -m "feat: add physics engine — entropy, sun distribution, death checks"
```

---

### Task 4: Agent Behavior

**Files:**
- Create: `agents/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write failing tests for agent think() and name generation**

`tests/test_agent.py`:
```python
"""Tests for agent decision logic."""
import random
import pytest
from world.state import create_agent, create_world
from agents.agent import think, generate_name, generate_child_name
import config


class TestThink:
    def test_works_when_tokens_below_danger(self):
        agent = create_agent("a1", "Ada-0", tokens=3.0)
        world = create_world()
        world.agents["a1"] = agent

        action = think(agent, world)

        assert action == "work"

    def test_works_when_tokens_at_danger(self):
        agent = create_agent("a1", "Ada-0", tokens=config.DANGER_THRESHOLD)
        world = create_world()
        world.agents["a1"] = agent

        action = think(agent, world)

        assert action == "work"

    def test_rests_when_tokens_moderate(self):
        """With tokens between danger and reproduce threshold, agent rests."""
        agent = create_agent("a1", "Ada-0", tokens=15.0)
        world = create_world()
        world.agents["a1"] = agent

        action = think(agent, world)

        assert action == "rest"

    def test_can_reproduce_when_wealthy(self):
        """With tokens above threshold and favorable random, agent reproduces."""
        agent = create_agent("a1", "Ada-0", tokens=35.0)
        world = create_world()
        world.agents["a1"] = agent

        random.seed(42)
        # Run multiple times to hit a reproduce
        actions = set()
        for seed in range(100):
            random.seed(seed)
            actions.add(think(agent, world))

        assert "reproduce" in actions

    def test_never_reproduces_below_threshold(self):
        """Even with favorable random, won't reproduce below threshold."""
        agent = create_agent("a1", "Ada-0", tokens=15.0)
        world = create_world()
        world.agents["a1"] = agent

        for seed in range(100):
            random.seed(seed)
            action = think(agent, world)
            assert action != "reproduce"


class TestNameGeneration:
    def test_generate_name_returns_string(self):
        name = generate_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_generate_child_name(self):
        name = generate_child_name("Ada-0", child_number=1)
        assert name == "Ada-1"

    def test_generate_child_name_from_child(self):
        name = generate_child_name("Ada-3", child_number=2)
        assert name == "Ada-2"

    def test_generate_child_name_preserves_stem(self):
        name = generate_child_name("Nova-0", child_number=5)
        assert name == "Nova-5"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/test_agent.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.agent'`

- [ ] **Step 3: Implement agent.py**

`agents/agent.py`:
```python
"""Nooscape agent behavior — Phase 0 rule-based logic.

No LLM calls. The goal is to prove the physics works, not that agents
are intelligent. Smart agents come in Phase 1.
"""
import random
from world.state import Agent, WorldState
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


def think(agent: Agent, world: WorldState) -> str:
    """Decide what action the agent takes this tick.

    Priority:
    1. If tokens < DANGER_THRESHOLD → 'work'
    2. If tokens > REPRODUCE_THRESHOLD and random chance → 'reproduce'
    3. Otherwise → 'rest'

    Returns one of: 'work', 'rest', 'reproduce'
    """
    if agent.tokens <= config.DANGER_THRESHOLD:
        return "work"

    if agent.tokens > config.REPRODUCE_THRESHOLD:
        if random.random() < config.REPRODUCE_CHANCE:
            return "reproduce"

    return "rest"
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/test_agent.py -v
```
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/agent.py tests/test_agent.py
git commit -m "feat: add agent think() logic and name generation"
```

---

### Task 5: SQLite Persistence

**Files:**
- Create: `world/persistence.py`
- Create: `tests/test_persistence.py`

- [ ] **Step 1: Write failing tests for save/load and events**

`tests/test_persistence.py`:
```python
"""Tests for SQLite persistence layer."""
import os
import pytest
from world.state import create_agent, create_world
from world.persistence import Database


@pytest.fixture
def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_nooscape.db")
    database = Database(db_path)
    yield database
    database.close()


class TestSnapshots:
    def test_save_and_load_snapshot(self, db):
        world = create_world()
        world.tick = 42
        agent = create_agent("a1", "Ada-0", tokens=15.5)
        world.agents["a1"] = agent
        world.total_tokens_minted = 100.0
        world.total_tokens_burned = 50.0

        db.save_snapshot(world)
        loaded = db.load_latest()

        assert loaded is not None
        assert loaded.tick == 42
        assert loaded.total_tokens_minted == 100.0
        assert loaded.total_tokens_burned == 50.0
        assert "a1" in loaded.agents
        assert loaded.agents["a1"].tokens == 15.5

    def test_load_latest_returns_most_recent(self, db):
        world1 = create_world()
        world1.tick = 10
        world1.agents["a1"] = create_agent("a1", "Ada-0", tokens=20.0)
        db.save_snapshot(world1)

        world2 = create_world()
        world2.tick = 20
        world2.agents["a1"] = create_agent("a1", "Ada-0", tokens=5.0)
        db.save_snapshot(world2)

        loaded = db.load_latest()

        assert loaded.tick == 20
        assert loaded.agents["a1"].tokens == 5.0

    def test_load_latest_returns_none_when_empty(self, db):
        loaded = db.load_latest()
        assert loaded is None


class TestEvents:
    def test_log_and_retrieve_events(self, db):
        db.log_event(10, "birth", "a1", {"name": "Ada-0"})
        db.log_event(15, "death", "a2", {"name": "Rex-0"})

        events = db.get_events(from_tick=0, to_tick=20)

        assert len(events) == 2
        assert events[0]["event_type"] == "birth"
        assert events[1]["event_type"] == "death"

    def test_get_events_filters_by_tick_range(self, db):
        db.log_event(5, "birth", "a1", {})
        db.log_event(15, "death", "a1", {})
        db.log_event(25, "birth", "a2", {})

        events = db.get_events(from_tick=10, to_tick=20)

        assert len(events) == 1
        assert events[0]["tick"] == 15

    def test_get_recent_events(self, db):
        for i in range(20):
            db.log_event(i, "work", f"a{i}", {})

        events = db.get_recent_events(limit=5)

        assert len(events) == 5
        assert events[0]["tick"] == 19  # most recent first
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/test_persistence.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'world.persistence'`

- [ ] **Step 3: Implement persistence.py**

`world/persistence.py`:
```python
"""Nooscape persistence layer — SQLite save/load for world state.

Single file database: nooscape.db
Two tables: snapshots (full world state) and events (birth, death, etc.)
"""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from world.state import WorldState


class Database:
    """SQLite database for world state persistence."""

    def __init__(self, db_path: str = "nooscape.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                tick INTEGER PRIMARY KEY,
                world_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tick INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                details TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_events_tick ON events(tick);
        """)
        self.conn.commit()

    def save_snapshot(self, world: WorldState) -> None:
        """Save a full world state snapshot at the current tick."""
        world_json = json.dumps(world.to_dict())
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO snapshots (tick, world_json, timestamp) VALUES (?, ?, ?)",
            (world.tick, world_json, now),
        )
        self.conn.commit()

    def load_latest(self) -> Optional[WorldState]:
        """Load the most recent world state snapshot. Returns None if empty."""
        row = self.conn.execute(
            "SELECT world_json FROM snapshots ORDER BY tick DESC LIMIT 1"
        ).fetchone()

        if row is None:
            return None

        data = json.loads(row["world_json"])
        return WorldState.from_dict(data)

    def log_event(self, tick: int, event_type: str, agent_id: str, details: dict) -> None:
        """Log a world event (birth, death, work, reproduce)."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO events (tick, event_type, agent_id, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (tick, event_type, agent_id, json.dumps(details), now),
        )
        self.conn.commit()

    def get_events(self, from_tick: int, to_tick: int) -> list:
        """Get events within a tick range (inclusive)."""
        rows = self.conn.execute(
            "SELECT tick, event_type, agent_id, details FROM events WHERE tick >= ? AND tick <= ? ORDER BY tick",
            (from_tick, to_tick),
        ).fetchall()

        return [
            {
                "tick": row["tick"],
                "event_type": row["event_type"],
                "agent_id": row["agent_id"],
                "details": json.loads(row["details"]),
            }
            for row in rows
        ]

    def get_recent_events(self, limit: int = 10) -> list:
        """Get the most recent events, newest first."""
        rows = self.conn.execute(
            "SELECT tick, event_type, agent_id, details FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [
            {
                "tick": row["tick"],
                "event_type": row["event_type"],
                "agent_id": row["agent_id"],
                "details": json.loads(row["details"]),
            }
            for row in rows
        ]

    def close(self):
        """Close the database connection."""
        self.conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/test_persistence.py -v
```
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add world/persistence.py tests/test_persistence.py
git commit -m "feat: add SQLite persistence for snapshots and events"
```

---

### Task 6: Simulation Runner

**Files:**
- Create: `simulation/runner.py`
- Create: `tests/test_runner.py`

- [ ] **Step 1: Write failing tests for world initialization and tick processing**

`tests/test_runner.py`:
```python
"""Tests for the simulation runner."""
import pytest
from world.state import create_world, create_agent
from simulation.runner import initialize_world, run_tick
import config


class TestInitializeWorld:
    def test_creates_genesis_agents(self):
        world = initialize_world()

        living = world.get_living_agents()
        assert len(living) == config.GENESIS_AGENT_COUNT

    def test_genesis_agents_have_starting_tokens(self):
        world = initialize_world()

        for agent in world.agents.values():
            assert agent.tokens == config.STARTING_TOKENS

    def test_genesis_agents_are_generation_zero(self):
        world = initialize_world()

        for agent in world.agents.values():
            assert agent.generation == 0
            assert agent.parent_id is None

    def test_genesis_agents_have_unique_ids(self):
        world = initialize_world()

        ids = [a.id for a in world.agents.values()]
        assert len(ids) == len(set(ids))


class TestRunTick:
    def test_advances_tick(self):
        world = initialize_world()

        new_world, events = run_tick(world)

        assert new_world.tick == 1

    def test_returns_events_list(self):
        world = initialize_world()

        new_world, events = run_tick(world)

        assert isinstance(events, list)

    def test_agents_can_work(self):
        """An agent in the danger zone should work and gain tokens."""
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=3.0)

        new_world, events = run_tick(world)

        # After entropy (3.0 - 0.5 = 2.5), sun (+ 10.0 = 12.5), work (+ 2.0 = 14.5)
        assert new_world.agents["a1"].tokens == pytest.approx(14.5)

    def test_reproduction_creates_child(self):
        """Force a reproduction by giving agent high tokens and seeding random."""
        import random
        world = create_world()
        world.agents["a1"] = create_agent("a1", "Ada-0", tokens=50.0)

        # Try many seeds until we get a reproduce
        child_created = False
        for seed in range(200):
            random.seed(seed)
            test_world = create_world()
            test_world.agents["a1"] = create_agent("a1", "Ada-0", tokens=50.0)
            new_world, events = run_tick(test_world)
            if len(new_world.agents) > 1:
                child_created = True
                # Verify child properties
                children = [a for a in new_world.agents.values() if a.id != "a1"]
                assert len(children) == 1
                child = children[0]
                assert child.generation == 1
                assert child.parent_id == "a1"
                assert child.tokens == config.CHILD_STARTING_TOKENS
                break

        assert child_created, "Reproduction never triggered across 200 random seeds"

    def test_dead_agents_dont_act(self):
        world = create_world()
        dead = create_agent("a1", "Ada-0", tokens=5.0)
        dead.alive = False
        world.agents["a1"] = dead

        new_world, events = run_tick(world)

        # Dead agent's tokens shouldn't change (no entropy, no sun, no actions)
        assert new_world.agents["a1"].tokens == 5.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/test_runner.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'simulation.runner'`

- [ ] **Step 3: Implement runner.py**

`simulation/runner.py`:
```python
"""Nooscape simulation runner — the heartbeat of the world.

Orchestrates physics ticks, agent decisions, and action processing.
"""
import uuid
from world.state import WorldState, create_agent, create_world
from world.physics import process_tick
from agents.agent import think, generate_name, generate_child_name
import config


def initialize_world() -> WorldState:
    """Create a fresh world with genesis agents."""
    world = create_world()

    for i in range(config.GENESIS_AGENT_COUNT):
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        name = generate_name()
        agent = create_agent(
            agent_id=agent_id,
            name=name,
            tokens=config.STARTING_TOKENS,
            born_tick=0,
            generation=0,
        )
        world.agents[agent_id] = agent

    return world


def run_tick(world: WorldState) -> tuple:
    """Run one complete tick: physics + agent decisions + action processing.

    Returns (new_world_state, list_of_events).
    Events are dicts with keys: tick, event_type, agent_id, details.
    """
    events = []

    # 1. Apply physics (entropy, sun, deaths)
    new_world = process_tick(world)

    # Record deaths from physics
    for agent_id, agent in new_world.agents.items():
        old_agent = world.agents.get(agent_id)
        if old_agent and old_agent.alive and not agent.alive:
            events.append({
                "tick": new_world.tick,
                "event_type": "death",
                "agent_id": agent_id,
                "details": {"name": agent.name, "generation": agent.generation},
            })

    # 2. Agent decisions and action processing
    living = new_world.get_living_agents()
    children_to_add = []

    for agent in living:
        action = think(agent, new_world)

        if action == "work":
            agent.tokens += config.WORK_REWARD
            events.append({
                "tick": new_world.tick,
                "event_type": "work",
                "agent_id": agent.id,
                "details": {"reward": config.WORK_REWARD},
            })

        elif action == "reproduce":
            if agent.tokens >= config.REPRODUCTION_COST:
                agent.tokens -= config.REPRODUCTION_COST

                # Count existing children of this parent for naming
                existing_children = sum(
                    1 for a in new_world.agents.values()
                    if a.parent_id == agent.id
                )
                child_number = existing_children + 1

                child_id = f"agent_{uuid.uuid4().hex[:8]}"
                child_name = generate_child_name(agent.name, child_number)
                child = create_agent(
                    agent_id=child_id,
                    name=child_name,
                    tokens=config.CHILD_STARTING_TOKENS,
                    born_tick=new_world.tick,
                    generation=agent.generation + 1,
                    parent_id=agent.id,
                )
                children_to_add.append(child)

                events.append({
                    "tick": new_world.tick,
                    "event_type": "reproduce",
                    "agent_id": agent.id,
                    "details": {
                        "child_id": child_id,
                        "child_name": child_name,
                        "cost": config.REPRODUCTION_COST,
                    },
                })

        # 'rest' — no-op

    # Add children after iterating (don't modify dict during iteration)
    for child in children_to_add:
        new_world.agents[child.id] = child

    return new_world, events
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/test_runner.py -v
```
Expected: All 7 tests PASS

- [ ] **Step 5: Run full test suite**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/ -v
```
Expected: All tests PASS (state + physics + agent + persistence + runner)

- [ ] **Step 6: Commit**

```bash
git add simulation/runner.py tests/test_runner.py
git commit -m "feat: add simulation runner — tick loop, action processing, reproduction"
```

---

### Task 7: CLI Observer (Terminal Display)

**Files:**
- Create: `cli/observe.py`

No tests for this task — it's pure display logic using the `rich` library. Verified visually.

- [ ] **Step 1: Implement observe.py**

`cli/observe.py`:
```python
"""Nooscape CLI observer — live terminal display using rich.

Shows world stats, living agents with token bars, and recent events.
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.live import Live

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
```

- [ ] **Step 2: Commit**

```bash
git add cli/observe.py
git commit -m "feat: add CLI observer with rich terminal display"
```

---

### Task 8: Main Entry Point — Wire It All Together

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement main.py**

`main.py`:
```python
"""Nooscape — main entry point.

Usage:
    python main.py           Fast mode (max speed, no display)
    python main.py --watch   Watch mode (live terminal, 1 tick/sec)
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

    # Set random seed if provided
    if args.seed is not None:
        import random
        random.seed(args.seed)

    console = Console()

    # Initialize database
    db = Database("nooscape.db")

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
```

- [ ] **Step 2: Test manually — fast mode (short run)**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python main.py --seed 42 --fresh
```
Let it run for ~10 seconds, then press Ctrl+C. Expected: status lines showing tick count, living/dead counts, tokens minted.

- [ ] **Step 3: Test manually — watch mode**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python main.py --watch --seed 42 --fresh
```
Expected: live terminal display showing agents with token bars, events appearing as they happen. Let it run for ~30 seconds, then press Ctrl+C.

- [ ] **Step 4: Test resume from save**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python main.py --watch
```
Expected: resumes from last saved tick (should say "Resumed from tick X with Y living agents").

- [ ] **Step 5: Run full test suite one final time**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -m pytest tests/ -v
```
Expected: All tests PASS

- [ ] **Step 6: Add .gitignore and commit**

`.gitignore`:
```
__pycache__/
*.pyc
*.db
.env
.venv/
```

```bash
git add main.py cli/observe.py .gitignore
git commit -m "feat: add main entry point with fast/watch modes and resume support"
```

---

### Task 9: Final Integration Test — The Overnight Run

- [ ] **Step 1: Run a deterministic 10,000 tick simulation**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python main.py --seed 42 --fresh
```
Let it run until it hits ~10,000 ticks (should take under a minute in fast mode), then Ctrl+C.

- [ ] **Step 2: Verify the world changed**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -c "
from world.persistence import Database
db = Database('nooscape.db')
world = db.load_latest()
living = world.get_living_agents()
dead = [a for a in world.agents.values() if not a.alive]
print(f'Final tick: {world.tick}')
print(f'Living agents: {len(living)}')
print(f'Dead agents: {len(dead)}')
print(f'Total agents ever: {len(world.agents)}')
print(f'Tokens minted: {world.total_tokens_minted:.1f}')
print(f'Tokens burned: {world.total_tokens_burned:.1f}')
print()
print('Living agents:')
for a in sorted(living, key=lambda x: x.tokens, reverse=True):
    print(f'  {a.name:<12} gen={a.generation} tokens={a.tokens:.1f} born=tick {a.born_tick}')
print()
print('Max generation:', max((a.generation for a in world.agents.values()), default=0))
db.close()
"
```

Expected output should show:
- Tick count in the thousands
- Some genesis agents dead
- Some agents born (generation > 0)
- Population different from starting 10
- Tokens minted and burned in meaningful amounts

- [ ] **Step 3: Verify events in database**

Run:
```bash
cd E:/Anti/Nooscape/Build/nooscape-os
python -c "
from world.persistence import Database
db = Database('nooscape.db')
events = db.get_recent_events(limit=20)
for e in events:
    print(f'  [{e[\"tick\"]}] {e[\"event_type\"]}: {e[\"agent_id\"][:12]} {e.get(\"details\", {})}')
print()
births = len(db.get_events(0, 999999))
print(f'Total events logged: {births}')
db.close()
"
```

- [ ] **Step 4: Final commit — Phase 0 complete**

```bash
git add -A
git commit -m "Phase 0: Proof of Life — complete

A single-node Python simulation where agents are born, live, earn
tokens, drain entropy, reproduce, and die autonomously.

Run with: python main.py --watch
Leave overnight: python main.py --seed 42"
```

---

## Success Checklist

After all tasks are complete, verify:

- [ ] `python main.py --watch --seed 42 --fresh` shows live terminal display with agents
- [ ] Agents with low tokens work, wealthy agents occasionally reproduce
- [ ] Agents die when tokens reach zero
- [ ] Population fluctuates over time (not monotonically growing or shrinking)
- [ ] `python main.py --seed 42 --fresh` runs at high speed with periodic status reports
- [ ] Stopping and restarting without `--fresh` resumes from last snapshot
- [ ] `python -m pytest tests/ -v` — all tests pass
- [ ] `world/physics.py` has zero side effects — confirmed by tests
- [ ] The simulation is deterministic with the same `--seed` value
