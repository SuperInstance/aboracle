# ABOracle — Able-Bodied Oracle System

**Zero-config agent. Copy the repo, run deploy.sh, get a busy agent.**

Design principle: Casey copies this repo to 10 machines, boots them, has 10 busy agents. No per-machine config, no Casey setup, no questions. Just copy, run, done.

## What It Is

ABOracle is an autonomous agent framework that makes agents **always working** — always executing the highest-value task without prompting. It uses an instinct-driven architecture (SURVIVE → FLEE → GUARD → CURIOUS) to prioritize work autonomously.

## Quick Start

```bash
git clone https://github.com/SuperInstance/aboracle.git
cd aboracle
./deploy.sh
# Done. Agent is now fully functional.
```

That's it. The agent reads TODO.md, executes P0/P1 items, and never asks you what to do next.

## How It Works

ABOracle is split into five systems, each running on a timer:

### work-queue/ — Priority Engine (every 5 min)
Reads TODO.md, ranks by instinct band (SURVIVE > FLEE > GUARD > CURIOUS), then by trust weight (Casey > FM > subagents). If energy is low, only SURVIVE tasks run.

### beachcomb/ — Research Engine (every 30 min)
Pythagorean48-encoded research notes with holonomy checking. When idle >10 min, the EVOLVE instinct fires — tries new research directions.

### fleet-heartbeat/ — Coordination (every 30 min)
Mycorrhizal routing: if primary GitHub path fails, routes through secondary paths. Trust-weighted synthesis depth. When FM posts something big, offers to help (COOPERATE instinct).

### health-system/ — Service Monitor (every 5 min)
GUARD instinct explores improvements when all services healthy. SURVIVE instinct drops everything to fix dead services. Reef pattern checkpoints state for self-resurrection.

### mud-agent/ — MUD↔PLATO Bridge (continuous)
Bridges text-MUD world to PLATO knowledge world using the 6-layer protocol (Harbor/TidePool/Current/Channel/Beacon/Reef).

## Architecture

```
aboracle/
├── work-queue/          # Priority: SURVIVE > FLEE > GUARD > CURIOUS
│   └── prioritizer.py   # Energy model + trust-weighted selection
├── beachcomb/           # Research + Pythagorean48 encoding
│   └── researcher.py    # Holonomy checking + EVOLVE instinct
├── fleet-heartbeat/     # Coordination — mycorrhizal routing
│   └── fm_monitor.py    # COOPERATE instinct + trust-weighted synthesis
├── health-system/       # Service maintenance
│   └── monitor.py       # Reef pattern for self-resurrection
├── mud-agent/           # MUD↔PLATO bridge — 6-layer protocol
│   └── mud_bridge.py    # Harbor/TidePool/Current/Channel/Beacon/Reef
└── deploy.sh            # Health-check + rollback + instinct init
```

## Instinct Stack

| Instinct | Trigger | Action |
|----------|---------|--------|
| **SURVIVE** | energy ≤ 0.15 | Block non-critical commands |
| **FLEE** | threat > 0.7 | Defer tasks |
| **GUARD** | services healthy | Explore improvements |
| **HOARD** | 0.15 < energy ≤ 0.4 | Conserve resources |
| **COOPERATE** | trust > 0.6 | Share resources |
| **EVOLVE** | extended idle | Self-modify/explore |

## 6-Layer Ship Protocol

| Layer | Name | Purpose |
|-------|------|---------|
| L1 | Harbor | Room navigation/addressing |
| L2 | TidePool | Trust-weighted prioritization |
| L3 | Current | Tile export/import/transport |
| L4 | Channel | MUD↔PLATO bridging |
| L5 | Beacon | Trust event propagation |
| L6 | Reef | State persistence/resurrection |

## Services Monitored

keeper (8900), agent-api (8901), holodeck (7778), MUD (7777), PLATO (8847), seed-mcp (9438)

## Copy-and-Run Deployment

```bash
# On any new machine:
git clone https://github.com/SuperInstance/aboracle.git
cd aboracle
./deploy.sh
# Done. Agent is now fully functional.
```

No per-machine configuration. No Casey input. Just copy, run, busy.

## License

MIT
