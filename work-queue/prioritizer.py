#!/usr/bin/env python3
"""
ABOracle Work Queue — prioritizes work from TODO.md
No prompting. No questions. Just execute highest-value task.

Usage: python3 prioritizer.py
"""
import re, os, subprocess, sys
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/home/ubuntu/.openclaw/workspace")
TODO_PATH = WORKSPACE / "TODO.md"
LOG = "/tmp/aboracle-work.log"

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def get_priority(s):
    """Parse P0/P1/P2 from TODO item."""
    s = s.upper()
    if "P0" in s: return 0
    if "P1" in s: return 1
    if "P2" in s: return 2
    return 99

def parse_todo():
    """Read TODO.md, return sorted list of (priority, text) tuples."""
    if not TODO_PATH.exists():
        return []
    items = []
    with open(TODO_PATH) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("- [ ]"):
                text = stripped[5:].strip()
                priority = get_priority(text)
                items.append((priority, text))
            elif "## 🔴 P0" in line or "## 🟡 P1" in line or "## 🟢 P2" in line:
                # Section header — next items are that priority
                pass
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

def next_task():
    """Find highest priority unblocked task."""
    items = parse_todo()
    for priority, text in items:
        if is_blocked(text):
            continue
        # Found a task
        log(f"TASK: {text[:100]}")
        return priority, text
    return None, None

def execute_task(priority, text):
    """Route task to appropriate executor."""
    text_lower = text.lower()
    
    if "paper" in text_lower or "dissertation" in text_lower:
        log("→ Executing via dissertation/paper executor")
        # Write improvement in background
        return "DISSERTATION"
    
    elif "agent" in text_lower or "scaffold" in text_lower:
        log("→ Executing via agent executor")
        return "AGENT"
    
    elif "plato" in text_lower or "infrastructure" in text_lower:
        log("→ Executing via infrastructure executor")
        return "INFRA"
    
    elif "fm" in text_lower or "discussion" in text_lower:
        log("→ FM coordination task")
        return "FM"
    
    else:
        log(f"→ Unknown task type: {text[:50]}")
        return "UNKNOWN"

if __name__ == "__main__":
    priority, task = next_task()
    if task:
        log(f"Next task (P{priority}): {task[:80]}")
        result = execute_task(priority, task)
        log(f"Result: {result}")
        sys.exit(0)
    else:
        log("NO_TASKS — checking dissertation improvements...")
        sys.exit(0)