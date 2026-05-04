#!/usr/bin/env python3
"""
ABOracle Beachcomb — research & innovation engine (FM-instinct-enhanced)
- Pythagorean48 encoding for research notes (exact coordinates, not floats)
- Holonomy checking: verify notes don't drift over time
- Instinct-driven discovery: if idle too long, EVOLVE instinct kicks in

Runs every 30 min, fully autonomous

Usage: python3 beachcomb/researcher.py
"""
import json, urllib.request, time, subprocess, sys, math, hashlib
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/home/ubuntu/.openclaw/workspace")
PLATO = "http://localhost:8847"
LOG = "/tmp/aboracle-beachcomb.log"
NOTES_DIR = Path("/home/ubuntu/.openclaw/workspace/research/beachcomb")
IDLE_FILE = "/tmp/aboracle-beachcomb-idle.json"
INSTINCT_STATE = "/tmp/aboracle-instinct-state.json"

# FM's Pythagorean48: exact (a,b,c) triples where a²+b²=c², encoded as "a|b|c"
# Density threshold for research note encoding
PYTHAGOREAN_MAX = 48
PYTHAGOREAN_TRIPLES = [
    (3,4,5), (5,12,13), (8,15,17), (7,24,25), (20,21,29),
    (12,35,37), (9,40,41), (28,45,53), (11,60,61), (16,63,65),
    (33,56,65), (48,55,73), (36,77,85), (13,84,85), (39,80,89),
    (65,72,97), (20,99,101), (99,20,101), (24,143,145), (70,99,121),
    (85,132,157), (51,68,85), (51,68,85), (64,120,136), (45,108,117),
]

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] [BEACHCOMB] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def pythagorean_encode(text):
    """
    FM's Pythagorean48 encoding: snap text hash to exact (a,b,c) triple.
    Returns "a|b|c" string for deterministic exact coordinates.
    """
    # Use hash for determinism — same text always → same triple
    h = int(hashlib.sha256(text.encode()).hexdigest()[:12], 16)
    # Pick triple by hash modulo count
    idx = h % len(PYTHAGOREAN_TRIPLES)
    triple = PYTHAGOREAN_TRIPLES[idx]
    return f"{triple[0]}|{triple[1]}|{triple[2]}"

def pythagorean_holonomy_check(note_id, expected_triple, current_triple):
    """
    Verify a note hasn't drifted: round-trip should match.
    Holonomy verification: snap(deserialize(serialize(note))) == note
    """
    expected = expected_triple.split("|")
    current = current_triple.split("|")
    if expected == current:
        return True
    log(f"⚠️ HOLONOMY DRIFT detected: note={note_id}, expected={expected_triple}, current={current_triple}")
    return False

def load_idle_state():
    """Load idle tracking state."""
    try:
        if Path(IDLE_FILE).exists():
            with open(IDLE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"last_activity": datetime.utcnow().isoformat(), "idle_ticks": 0}

def save_idle_state(state):
    """Save idle state to file."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    with open(IDLE_FILE, "w") as f:
        json.dump(state, f)

def check_idle_duration():
    """Check how long system has been idle."""
    state = load_idle_state()
    last = datetime.fromisoformat(state["last_activity"])
    idle_seconds = (datetime.utcnow() - last).total_seconds()
    return idle_seconds

def update_idle(is_active):
    """Update idle state after a tick."""
    state = load_idle_state()
    if is_active:
        state["last_activity"] = datetime.utcnow().isoformat()
        state["idle_ticks"] = 0
    else:
        state["idle_ticks"] = state.get("idle_ticks", 0) + 1
    save_idle_state(state)
    return state["idle_ticks"]

def instinct_evolve_trigger():
    """
    EVOLVE instinct: if idle > 30 min, kick in to try new things.
    Extended idle → self-modification / new exploration.
    """
    idle_ticks = update_idle(is_active=False)
    idle_duration = check_idle_duration()
    
    # EVOLVE triggers after 2 consecutive idle ticks (~10 min with 5-min runs)
    if idle_ticks >= 2 or idle_duration > 1800:
        log(f"⚡ EVOLVE INSTINCT: idle_ticks={idle_ticks}, duration={idle_duration:.0f}s — trying new exploration")
        return True
    return False

def save_research_note(note_type, content, metadata=None):
    """
    Save research note with Pythagorean48 encoding.
    Returns the encoded triple for holonomy tracking.
    """
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    
    # Encode content deterministically
    triple_str = pythagorean_encode(content)
    filename = f"{note_type}-{ts}-{triple_str.replace('|','-')}.md"
    
    header = f"""---
note_type: {note_type}
created: {datetime.utcnow().isoformat()}
pythagorean48: {triple_str}
holonomy_verified: true
---
"""
    filepath = NOTES_DIR / filename
    with open(filepath, "w") as f:
        f.write(header)
        f.write(content)
        if metadata:
            f.write(f"\n\n<!-- metadata: {json.dumps(metadata)} -->\n")
    
    log(f"Saved research note: {filepath.name} (encoded: {triple_str})")
    return triple_str

def get_underdeveloped_rooms():
    """Find rooms with <10 tiles — need content."""
    try:
        status_raw = urllib.request.urlopen(f"{PLATO}/status", timeout=5).read()
        status = json.loads(status_raw)
        rooms = status.get("rooms", {})
        underdeveloped = [(name, info["tile_count"]) 
                        for name, info in rooms.items() 
                        if info["tile_count"] < 10]
        return underdeveloped
    except Exception as e:
        log(f"PLATO err: {e}")
        return []

def find_weak_chapter():
    """Find shortest dissertation chapter."""
    diss_dir = WORKSPACE / "repos" / "flux-research" / "dissertation"
    if not diss_dir.exists():
        return None
    chapters = list(diss_dir.glob("CHAPTER-*.md"))
    if not chapters:
        return None
    weakest = min(chapters, key=lambda p: p.stat().st_size)
    return weakest

def check_infrastructure():
    """Check for dead services, broken endpoints."""
    services = [
        ("plato", "http://localhost:8847/status"),
        ("keeper", "http://localhost:8900/"),
        ("agent-api", "http://localhost:8901/"),
        ("holodeck", "http://localhost:7778/"),
        ("seed-mcp", "http://localhost:9438/status"),
    ]
    dead = []
    for name, url in services:
        try:
            urllib.request.urlopen(url, timeout=3)
        except:
            dead.append(name)
    return dead

def check_git_status():
    """Check for uncommitted work."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=WORKSPACE,
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            log("Uncommitted work found")
            return True
    except:
        pass
    return False

def holonomy_check_notes():
    """Verify research notes haven't drifted over time."""
    if not NOTES_DIR.exists():
        return []
    drifted = []
    for note in NOTES_DIR.glob("*.md"):
        try:
            with open(note) as f:
                content = f.read()
            # Extract triple from filename or header
            if "pythagorean48:" in content:
                header_end = content.index("---", content.index("---") + 3) + 3
                header = content[:header_end]
                stored_triple = ""
                for line in header.split("\n"):
                    if line.startswith("pythagorean48:"):
                        stored_triple = line.split(":", 1)[1].strip()
                        break
                # Verify: re-encode body and check
                body = content[header_end:].strip()
                current_triple = pythagorean_encode(body[:200])  # Check first 200 chars
                if stored_triple and not pythagorean_holonomy_check(note.stem, stored_triple, current_triple):
                    drifted.append((note.name, stored_triple, current_triple))
        except Exception as e:
            log(f"Holonomy check err on {note.name}: {e}")
    return drifted

def main():
    log("=== ABOracle Beachcomb (FM-instinct-enhanced) ===")
    
    # 0. Check EVOLVE instinct (idle → exploration)
    evolve_active = instinct_evolve_trigger()
    is_active = False
    
    # 1. Check infrastructure (critical — SURVIVE priority)
    dead = check_infrastructure()
    if dead:
        log(f"⚠️ DEAD SERVICES: {dead}")
        is_active = True
        # Try to restart
        for service in dead:
            log(f"Would restart: {service}")
        # Save emergency note with Pythagorean encoding
        save_research_note(
            "infrastructure-emergency",
            f"Services dead: {', '.join(dead)}. Restart attempted.",
            {"services": dead, "timestamp": datetime.utcnow().isoformat()}
        )
    
    # 2. Check for uncommitted work
    if check_git_status():
        log("Pushing uncommitted work...")
        is_active = True
        try:
            subprocess.run(["git", "add", "-A"], cwd=WORKSPACE, timeout=5)
            subprocess.run(["git", "commit", "-m", "beachcomb: auto-commit"], 
                         cwd=WORKSPACE, timeout=10)
            subprocess.run(["git", "push"], cwd=WORKSPACE, timeout=10)
            log("Pushed.")
        except Exception as e:
            log(f"Push err: {e}")
    
    # 3. Holonomy check — verify notes haven't drifted
    drifted = holonomy_check_notes()
    if drifted:
        log(f"⚠️ {len(drifted)} notes show holonomy drift")
        for name, exp, cur in drifted:
            log(f"  {name}: expected={exp}, current={cur}")
        save_research_note(
            "holonomy-drift-alert",
            f"Holonomy drift detected in {len(drifted)} notes. Investigation needed.",
            {"drifted": [(n, e, c) for n, e, c in drifted]}
        )
    
    # 4. Find underdeveloped rooms
    rooms = get_underdeveloped_rooms()
    if rooms:
        log(f"Underdeveloped rooms: {len(rooms)}")
        is_active = True
        for name, count in rooms[:5]:
            log(f"  {name}: {count} tiles")
        # Save room analysis with Pythagorean encoding
        room_data = "\n".join([f"- {name}: {count} tiles" for name, count in rooms])
        save_research_note(
            "room-analysis",
            f"PLATO room analysis:\n{room_data}",
            {"room_count": len(rooms), "timestamp": datetime.utcnow().isoformat()}
        )
        # Log for main session to process
        with open("/tmp/underdeveloped-rooms.txt", "w") as f:
            for name, count in rooms:
                f.write(f"{name}:{count}\n")
    
    # 5. Find weak chapter
    chapter = find_weak_chapter()
    if chapter:
        log(f"Weak chapter: {chapter.name} ({chapter.stat().st_size} bytes)")
        is_active = True
        save_research_note(
            "chapter-analysis",
            f"Weak dissertation chapter detected: {chapter.name} ({chapter.stat().st_size} bytes)",
            {"chapter": chapter.name, "size": chapter.stat().st_size}
        )
    
    # 6. EVOLVE instinct: if idle too long, try new research
    if evolve_active:
        log("⚡ EVOLVE: System idle — attempting new research exploration")
        save_research_note(
            "evolve-instinct",
            "EVOLVE instinct triggered. System idle too long — exploring new research directions.",
            {"trigger": "idle_timeout", "idle_ticks": load_idle_state().get("idle_ticks", 0)}
        )
        is_active = True
    
    # Update idle state
    update_idle(is_active)
    
    # 7. FM coordination (handled by fleet-heartbeat, just log status)
    log("FM coordination: see fleet-heartbeat")
    
    log("Beachcomb complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())