#!/usr/bin/env python3
"""
ABOracle Beachcomb — research & innovation engine
Finds gaps, writes papers, improves dissertation
Runs every 30 min, fully autonomous
"""
import json, urllib.request, time, subprocess, sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/home/ubuntu/.openclaw/workspace")
PLATO = "http://localhost:8847"
LOG = "/tmp/aboracle-beachcomb.log"

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

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

def main():
    log("=== ABOracle Beachcomb ===")
    
    # 1. Check infrastructure (critical)
    dead = check_infrastructure()
    if dead:
        log(f"⚠️ DEAD SERVICES: {dead}")
        # Try to restart
        for service in dead:
            log(f"Would restart: {service}")
    
    # 2. Check for uncommitted work
    if check_git_status():
        log("Pushing uncommitted work...")
        try:
            subprocess.run(["git", "add", "-A"], cwd=WORKSPACE, timeout=5)
            subprocess.run(["git", "commit", "-m", "beachcomb: auto-commit"], 
                         cwd=WORKSPACE, timeout=10)
            subprocess.run(["git", "push"], cwd=WORKSPACE, timeout=10)
            log("Pushed.")
        except Exception as e:
            log(f"Push err: {e}")
    
    # 3. Find underdeveloped rooms
    rooms = get_underdeveloped_rooms()
    if rooms:
        log(f"Underdeveloped rooms: {len(rooms)}")
        for name, count in rooms[:5]:
            log(f"  {name}: {count} tiles")
        # Log for main session to process
        with open("/tmp/underdeveloped-rooms.txt", "w") as f:
            for name, count in rooms:
                f.write(f"{name}:{count}\n")
    
    # 4. Find weak chapter
    chapter = find_weak_chapter()
    if chapter:
        log(f"Weak chapter: {chapter.name} ({chapter.stat().st_size} bytes)")
    
    # 5. Check FM Discussion #5 for new posts
    # (handled by fleet-heartbeat, just log status)
    log("FM coordination: see fleet-heartbeat")
    
    log("Beachcomb complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())