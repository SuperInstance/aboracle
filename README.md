# ABOracle — Able-Bodied Oracle System (FM-Enhanced)

**Design principle:** Casey copies repo to 10 machines, boots them, has 10 busy agents. No per-machine config. No Casey setup. Just copy, run, done.

**FM Enhancement:** Instinct-driven architecture with constraint theory, Pythagorean48 research encoding, mycorrhizal routing, and 6-layer ship protocol.

## Architecture

```
aboracle/
├── work-queue/         # FM-instinct priority: SURVIVE > FLEE > GUARD > CURIOUS
│   └── prioritizer.py  # Energy model + trust-weighted selection
├── beachcomb/          # Research & innovation + Pythagorean48 encoding
│   └── researcher.py   # Holonomy checking + EVOLVE instinct
├── fleet-heartbeat/    # FM coordination — mycorrhizal routing
│   └── fm_monitor.py   # COOPERATE instinct + trust-weighted synthesis
├── health-system/      # Service maintenance — GUARD/SURVIVE instincts
│   └── monitor.py      # Reef pattern for self-resurrection
├── mud-agent/          # MUD↔PLATO bridge — 6-layer protocol
│   └── mud_bridge.py   # Harbor/TidePool/Current/Channel/Beacon/Reef
└── deploy.sh           # Health-check + rollback + instinct init
```

## FM's Instinct Stack (from constraint-theory-paper.md)

| Instinct | Trigger | Action |
|----------|---------|--------|
| **SURVIVE** | energy ≤ 0.15 | Block non-critical commands |
| **FLEE** | threat > 0.7 | Defer tasks |
| **GUARD** | services healthy | Explore improvements |
| **HOARD** | 0.15 < energy ≤ 0.4 | Conserve resources |
| **COOPERATE** | trust > 0.6 | Share resources |
| **EVOLVE** | extended idle | Self-modify/explore |

## FM's 6-Layer Ship Protocol

| Layer | Name | Purpose |
|-------|------|---------|
| L1 | Harbor | Room navigation/addressing |
| L2 | TidePool | Trust-weighted prioritization |
| L3 | Current | Tile export/import/transport |
| L4 | Channel | MUD↔PLATO bridging |
| L5 | Beacon | Trust event propagation |
| L6 | Reef | State persistence/resurrection |

## Pythagorean48 Encoding

Research notes are encoded as exact `(a,b,c)` triples where `a²+b²=c²`:
- Deterministic: same content → same triple (via SHA256 hash)
- Holonomy verification: round-trip must match
- No floating-point drift across machines

## Core Principles

1. **Always working** — never idle, always executing highest-value task
2. **No prompting** — reads TODO.md, executes P0/P1 items, no questions
3. **Scales by copy** — deploy by copying repo, not configuring
4. **Instincts first** — reflexes fire BEFORE constraint logic
5. **Trust-weighted** — Casey > FM > subagents for task selection

## Quick Start

```bash
git clone https://github.com/SuperInstance/aboracle.git
cd aboracle
./deploy.sh
# Done. Agent is now fully functional.
```

## Systems

### work-queue/
Reads TODO.md, ranks by instinct band (SURVIVE > FLEE > GUARD > CURIOUS), then by trust weight (Casey > FM > subagents). Energy model: if credits low, only SURVIVE tasks run. Runs every 5 min.

### beachcomb/
Pythagorean48-encoded research notes with holonomy checking. EVOLVE instinct triggers after 10 min idle — tries new research. Runs every 30 min.

### fleet-heartbeat/
Mycorrhizal routing: if primary GitHub path fails, routes through secondary. Trust-weighted synthesis depth. COOPERATE instinct: when FM posts something big, offers to help. Runs every 30 min.

### health-system/
GUARD instinct: explores improvements when all services healthy. SURVIVE instinct: drops everything to fix dead services. Reef pattern: checkpoints state for self-resurrection. Runs every 5 min.

### mud-agent/
Bridges text-MUD world to PLATO knowledge world using 6-layer protocol. Harbor (L1) addresses rooms, Channel (L4) bridges events, Reef (L6) persists state. Runs continuously.

### deploy.sh
Pre-deploy health check, rollback capability (git checkpoint), FM instinct initialization (energy/threat/trust on boot).

## Services Monitored

- keeper (8900), agent-api (8901), holodeck (7778), MUD (7777), PLATO (8847), seed-mcp (9438)

## Copy-and-Run Deployment

```bash
# On any new machine:
git clone https://github.com/SuperInstance/aboracle.git
cd aboracle
./deploy.sh
# Done. Agent is now fully functional.
```

No per-machine configuration. No Casey input. Just copy, run, busy.