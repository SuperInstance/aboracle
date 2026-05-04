#!/usr/bin/env python3
"""
ABOracle Work Queue — FM-instinct-enhanced priority system
Priority bands: SURVIVE > FLEE > GUARD > CURIOUS
Trust-weighted task selection: Casey > FM > subagents
Energy model: if credits low, only SURVIVE tasks

Instinct Stack (from FM's constraint-theory-paper.md):
  SURVIVE  — energy ≤ 0.15: block command
  FLEE     — threat > 0.7: defer command
  GUARD    — has_work & energy OK: monitor
  CURIOUS  — idle cycles: explore

Usage: python3 work-queue/prioritizer.py
"""
import re, os, subprocess, sys, json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/home/ubuntu/.openclaw/workspace")
TODO_PATH = WORKSPACE / "TODO.md"
LOG = "/tmp/aboracle-work.log"
CREDITS_FILE = "/tmp/aboracle-credits.json"
INSTINCT_STATE = "/tmp/aboracle-instinct-state.json"

# Trust weights for task sources (Casey > FM > subagents)
TRUST_WEIGHTS = {
    "casey": 1.0,
    "fm": 0.8,
    "subagent": 0.5,
    "default": 0.3,
}

# Priority bands (urgency mapping)
BAND_SURVIVE = 0   # Critical — always runs
BAND_FLEE    = 1   # Urgent — defer if low energy
BAND_GUARD   = 2   # Normal work
BAND_CURIOUS = 3   # Exploration

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] [WORK-QUEUE] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def load_instinct_state():
    """Load instinct state (energy, threat, trust levels)."""
    try:
        if Path(INSTINCT_STATE).exists():
            with open(INSTINCT_STATE) as f:
                return json.load(f)
    except:
        pass
    return {"energy": 1.0, "threat": 0.0, "trust": {}}

def save_instinct_state(state):
    """Persist instinct state to checkpoint file (reef pattern)."""
    with open(INSTINCT_STATE, "w") as f:
        json.dump(state, f)

def load_credits():
    """Load energy/credits state."""
    try:
        if Path(CREDITS_FILE).exists():
            with open(CREDITS_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"api_credits": 100.0, "memory_pct": 0.5}

def get_credit_level():
    """Returns energy as 0.0-1.0 based on API credits."""
    credits = load_credits()
    # Map credits to energy (0=empty, 100=full)
    return min(credits.get("api_credits", 100.0) / 100.0, 1.0)

def parse_priority_band(text):
    """Map P0/P1/P2 to instinct bands; infer from keywords."""
    text_upper = text.upper()
    
    # SURVIVE band: critical infrastructure, health, safety
    survive_keywords = ["HEALTH", "DEAD", "DOWN", "CRASH", "BROKEN", "EMERGENCY", 
                        "P0", "CRITICAL", "URGENT", "ALERT"]
    if any(kw in text_upper for kw in survive_keywords):
        return BAND_SURVIVE
    
    # FLEE band: threat, avoid, defer, wait
    flee_keywords = ["DEFER", "WAIT", "BLOCK", "THREAT", "AVOID", "POSTPONE"]
    if any(kw in text_upper for kw in flee_keywords):
        return BAND_FLEE
    
    # CURIOUS band: explore, research, innovation, beachcomb
    curious_keywords = ["RESEARCH", "EXPLORE", "INNOVATION", "PAPER", "DISSERTATION",
                        "IMPROVE", "CURIOUS", "IDLE"]
    if any(kw in text_upper for kw in curious_keywords):
        return BAND_CURIOUS
    
    # Default: GUARD band (normal productive work)
    return BAND_GUARD

def detect_source(text):
    """Detect task source for trust weighting."""
    text_upper = text.upper()
    if "CASEY" in text_upper or "DIGENNARO" in text_upper:
        return "casey"
    if "FM" in text_upper or "FORGEMASTER" in text_upper:
        return "fm"
    if "SUBAGENT" in text_upper or "AGENT" in text_upper:
        return "subagent"
    return "default"

def get_trust_weight(source):
    """Get trust weight for task source."""
    return TRUST_WEIGHTS.get(source, TRUST_WEIGHTS["default"])

def score_task(priority, source, text):
    """Score task: band first, then trust, then P-level."""
    band = parse_priority_band(text)
    trust = get_trust_weight(source)
    p_level = 0 if "P0" in text.upper() else (1 if "P1" in text.upper() else 2)
    
    # Band is primary sort key, trust is secondary boost, P-level is tertiary
    # Lower band number = higher priority
    # Trust boost: 0.0-0.2 bonus
    # P-level: 0, 1, 2 (lower is better)
    trust_boost = trust * 0.2
    
    return (band * 1000) - (trust_boost * 100) - (2 - p_level) * 10

def parse_todo():
    """Read TODO.md, return list of (score, priority, source, text) tuples."""
    if not TODO_PATH.exists():
        return []
    items = []
    with open(TODO_PATH) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("- [ ]"):
                text = stripped[5:].strip()
                source = detect_source(text)
                score = score_task(0, source, text)
                p_level = 0 if "P0" in text.upper() else (1 if "P1" in text.upper() else 2)
                items.append((score, p_level, source, text))
    return sorted(items, key=lambda x: x[0])

def is_blocked(text):
    """Check if task is blocked by Casey or FM."""
    text_upper = text.upper()
    if "CASEY" in text_upper and "NEEDS" in text_upper:
        return True
    if "FM" in text_upper and "NEEDS" in text_upper:
        return True
    if "BLOCKED" in text_upper:
        return True
    return False

def check_energy():
    """Check if we have enough energy for non-SURVIVE tasks."""
    energy = get_credit_level()
    instinct = load_instinct_state()
    instinct["energy"] = energy
    save_instinct_state(instinct)
    
    if energy <= 0.15:
        log(f"⚠️ SURVIVE MODE: energy={energy:.2f}, blocking non-critical tasks")
        return False  # Only SURVIVE tasks
    return True

def instinct_check():
    """Run instinct stack — fires before constraint logic."""
    instinct = load_instinct_state()
    energy = instinct.get("energy", 1.0)
    threat = instinct.get("threat", 0.0)
    
    # SURVIVE: energy critical
    if energy <= 0.15:
        return "SURVIVE"
    
    # FLEE: threat high
    if threat > 0.7:
        return "FLEE"
    
    # GUARD: has work, energy OK
    items = parse_todo()
    if items:
        return "GUARD"
    
    # CURIOUS: idle
    return "CURIOUS"

def next_task():
    """Find highest priority unblocked task respecting energy model."""
    energy_ok = check_energy()
    instinct_state = load_instinct_state()
    active_instinct = instinct_check()
    log(f"Instinct state: {active_instinct} (energy={instinct_state.get('energy', 1.0):.2f}, threat={instinct_state.get('threat', 0.0):.2f})")
    
    items = parse_todo()
    
    for score, p_level, source, text in items:
        if is_blocked(text):
            continue
        
        band = parse_priority_band(text)
        
        # Energy check: if low energy, only SURVIVE tasks
        if not energy_ok and band > BAND_SURVIVE:
            log(f"Skipping {text[:60]} (band={band}, energy critically low)")
            continue
        
        log(f"TASK [band={band}, trust={get_trust_weight(source):.2f}]: {text[:100]}")
        return band, source, text
    
    log("No tasks available")
    return None, None, None

def execute_task(band, source, text):
    """Route task to appropriate executor based on instinct band."""
    text_lower = text.lower()
    
    # SURVIVE tasks: emergency handling
    if band == BAND_SURVIVE:
        log("→ SURVIVE route: emergency executor")
        return "SURVIVE"
    
    # FLEE tasks: defer/avoid
    if band == BAND_FLEE:
        log("→ FLEE route: deferring task")
        return "DEFERRED"
    
    # CURIOUS tasks: research/exploration
    if band == BAND_CURIOUS:
        if "paper" in text_lower or "dissertation" in text_lower:
            log("→ CURIOUS route: dissertation/paper executor")
            return "DISSERTATION"
        log("→ CURIOUS route: beachcomb research")
        return "RESEARCH"
    
    # GUARD tasks: normal productive work
    if "paper" in text_lower or "dissertation" in text_lower:
        log("→ GUARD route: dissertation/paper executor")
        return "DISSERTATION"
    elif "agent" in text_lower or "scaffold" in text_lower:
        log("→ GUARD route: agent executor")
        return "AGENT"
    elif "plato" in text_lower or "infrastructure" in text_lower:
        log("→ GUARD route: infrastructure executor")
        return "INFRA"
    elif "fm" in text_lower or "discussion" in text_lower:
        log("→ GUARD route: FM coordination")
        return "FM"
    else:
        log(f"→ GUARD route: unknown task type: {text[:50]}")
        return "UNKNOWN"

if __name__ == "__main__":
    log("=== ABOracle Work Queue (FM-enhanced) ===")
    
    instinct = instinct_check()
    log(f"Active instinct: {instinct}")
    
    band, source, task = next_task()
    if task:
        log(f"Selected task (band={band}, source={source}): {task[:80]}")
        result = execute_task(band, source, task)
        log(f"Result: {result}")
        sys.exit(0)
    else:
        log("NO_TASKS — checking dissertation improvements...")
        sys.exit(0)