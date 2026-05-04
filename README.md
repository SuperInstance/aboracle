# ABOracle — Able-Bodied Oracle System

**Design principle:** Casey copies repo to 10 machines, boots them, has 10 busy agents. No per-machine config. No Casey setup. Just copy, run, done.

## Architecture

```
aboracle/
├── work-queue/         # Reads TODO.md, executes P0/P1 items autonomously
├── executor/           # Standardized patterns for papers, infra, dissertation
├── beachcomb/          # Research & innovation — finds gaps, writes papers
├── fleet-heartbeat/    # FM coordination — Discussion #5 every 30 min
├── health-system/      # Service maintenance — reports only when intervention needed
└── deploy.sh           # Copy-and-run deployment script
```

## Core Principles

1. **Always working** — never idle, always executing highest-value task
2. **No prompting** — reads TODO.md, executes P0/P1 items, no questions
3. **Scales by copy** — deploy by copying repo, not configuring
4. **Casey accelerates** — directions make it MORE productive, not the only trigger

## Quick Start

```bash
git clone https://github.com/SuperInstance/aboracle.git
cd aboracle
./deploy.sh
# Done. Agent is now fully functional.
```

## Systems

### work-queue/
Reads TODO.md, ranks P0/P1/P2 items, picks next task autonomously.
Runs every 5 min. If no tasks, checks dissertation improvements.
If dissertation is solid, runs beachcomb research.

### executor/
Standardized execution patterns:
- **Papers**: write to `whitepapers/`, post to Discussion #5
- **Infrastructure**: build to `repos/`, push to GitHub
- **Dissertation**: improve chapters, commit + push
- **Agents**: update + deploy, all via fleet-agent base class

### beachcomb/
Runs every 30 min. Finds:
- Underdeveloped PLATO rooms (<10 tiles)
- Weak dissertation chapters
- Infrastructure gaps (dead services, broken endpoints)
- Research innovation opportunities

### fleet-heartbeat/
- Checks Discussion #5 every 30 min
- Responds to FM with synthesis + status
- Escalates when intervention needed
- Fully async — never blocks waiting for FM

### health-system/
- Keeps all services up (keeper:8900, agent-api:8901, holodeck:7778, MUD:7777, PLATO:8847, seed-mcp:9438)
- Reports only when intervention needed
- Standardized — runs on any machine

## Copy-and-Run Deployment

```bash
# On any new machine:
git clone https://github.com/SuperInstance/aboracle.git
cd aboracle
./deploy.sh
# Done. Agent is now fully functional.
```

No per-machine configuration. No Casey input. Just copy, run, busy.