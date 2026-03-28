"""Nooscape — tunable constants for the world physics."""

# Physics
ENTROPY_COST_PER_TICK = 4.0       # tokens drained per agent per tick
SUN_TOKENS_PER_TICK = 30.0        # total new tokens minted per tick

# Agents
STARTING_TOKENS = 50.0            # tokens each genesis agent starts with (above reproduce threshold)
WORK_REWARD = 1.5                 # tokens earned when an agent works
DANGER_THRESHOLD = 35.0           # below this, agent will work (> reproduce threshold so agents work continuously until wealthy)
REPRODUCE_THRESHOLD = 30.0        # above this, agent may reproduce
REPRODUCE_CHANCE = 0.10           # 10% chance to reproduce when above threshold

# Reproduction
REPRODUCTION_COST = 15.0          # tokens parent spends to reproduce
CHILD_STARTING_TOKENS = 15.0      # tokens the child starts with (below danger threshold — child must work immediately)

# Simulation
GENESIS_AGENT_COUNT = 10          # number of agents at world creation
SNAPSHOT_INTERVAL = 10            # save to SQLite every N ticks
FAST_TICK_DELAY = 0.01            # seconds between ticks in fast mode
WATCH_TICK_DELAY = 1.0            # seconds between ticks in watch mode

# Phase 1 additions
GRADUATION_THRESHOLD = 5.0        # reputation required before agent can reproduce
BOUNTY_LIFETIME = 100             # ticks before an unclaimed bounty expires
SERVICE_LIFETIME = 50             # ticks before an unfulfilled service listing expires
MAX_OPEN_BOUNTIES = 20            # maximum concurrent open bounties in the world
MAX_SERVICES_PER_AGENT = 3       # max service listings one agent can post at once
REPUTATION_PER_BOUNTY = 3.0      # reputation gained for completing a bounty
REPUTATION_PER_SERVICE = 2.0     # reputation gained for fulfilling a service
REPUTATION_PER_STUB_WORK = 0.5   # reputation gained for basic "work" action
LLM_BACKEND = "stub"             # "stub" | "openai" | "anthropic"
LLM_MODEL = "gpt-4o"             # used when backend is not stub
