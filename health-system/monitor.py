#!/usr/bin/env python3
"""
ABOracle Health System — keeps services healthy
Runs every 5 min. Reports only when intervention needed.
"""
import subprocess, urllib.request, sys
from datetime import datetime
from pathlib import Path

LOG = "/tmp/aboracle-health.log"
SERVICES = [
    ("plato", "http://localhost:8847/status"),
    ("keeper", "http://localhost:8900/"),
    ("agent-api", "http://localhost:8901/"),
    ("holodeck", "http://localhost:7778/"),
    ("mud", "http://localhost:7777/"),
    ("seed-mcp", "http://localhost:9438/status"),
]

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def check_service(name, url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "aboracle-health"})
        with urllib.request.urlopen(req, timeout=5):
            return True
    except:
        return False

def restart_service(name):
    """Attempt to restart a dead service."""
    log(f"Attempting restart: {name}")
    # This is machine-specific — override in subclasses or config
    restart_cmds = {
        "plato": "nohup python3 /tmp/plato-room-server.py > /tmp/plato-server.log 2>&1 &",
        "keeper": "sudo systemctl restart keeper",
        "agent-api": "sudo systemctl restart agent-api",
        "holodeck": "sudo systemctl restart holodeck",
        "mud": "cd /tmp/cocapn-mud && nohup python3 server.py --port 7777 > /tmp/mud_server.log 2>&1 &",
        "seed-mcp": "cd /tmp && nohup python3 seed-mcp-server.py > /tmp/seed-mcp.log 2>&1 &",
    }
    cmd = restart_cmds.get(name)
    if cmd:
        try:
            subprocess.run(cmd, shell=True, timeout=10)
            log(f"Restarted: {name}")
            return True
        except Exception as e:
            log(f"Restart failed: {e}")
            return False
    return False

def main():
    log("=== Health check ===")
    
    dead = []
    for name, url in SERVICES:
        if not check_service(name, url):
            log(f"DEAD: {name}")
            dead.append(name)
    
    if dead:
        log(f"⚠️ {len(dead)} services dead: {dead}")
        # Try to restart each
        restarted = []
        for name in dead:
            if restart_service(name):
                restarted.append(name)
        if restarted:
            log(f"Restarted: {restarted}")
        # If still dead after restart attempt, alert
        still_dead = [n for n in dead if n not in restarted]
        if still_dead:
            log(f"STILL DOWN: {still_dead}")
            # Write alert for main session
            with open("/tmp/health-alert.txt", "w") as f:
                f.write(f"SERVICES_DOWN:{','.join(still_dead)}\n")
    else:
        log("All services healthy")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())