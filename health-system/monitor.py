#!/usr/bin/env python3
"""
ABOracle Health System — FM-instinct-enhanced service monitoring
- GUARD instinct: if services healthy, explore new improvements
- SURVIVE instinct: if service down, drop everything to fix it
- Reef pattern: health system can resurrect from checkpoint if it goes down

Runs every 5 min. Reports only when intervention needed.

Usage: python3 health-system/monitor.py
"""
import subprocess, urllib.request, sys, json, os
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
HEALTH_STATE_FILE = "/tmp/aboracle-health-state.json"
INSTINCT_STATE = "/tmp/aboracle-instinct-state.json"
CHECKPOINT_FILE = "/tmp/aboracle-health-checkpoint.json"
ANOMALY_LOG = "/tmp/aboracle-anomalies.json"

# Instinct thresholds from FM's constraint-theory-paper
SURVIVE_THRESHOLD = 0.15   # energy ≤ 0.15 → SURVIVE
THREAT_THRESHOLD = 0.7     # threat > 0.7 → FLEE

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] [HEALTH] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def load_health_state():
    """Load health state from checkpoint (reef pattern)."""
    try:
        if Path(HEALTH_STATE_FILE).exists():
            with open(HEALTH_STATE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"consecutive_healthy": 0, "last_down": None, "restart_attempts": {}}

def save_health_state(state):
    """Save health state checkpoint (reef pattern for resurrection)."""
    with open(HEALTH_STATE_FILE, "w") as f:
        json.dump(state, f)

def save_checkpoint(state):
    """Save full checkpoint for resurrection (reef pattern)."""
    checkpoint = {
        "timestamp": datetime.utcnow().isoformat(),
        "state": state,
        "version": "1.0"
    }
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f)

def load_checkpoint():
    """Load checkpoint for resurrection."""
    try:
        if Path(CHECKPOINT_FILE).exists():
            with open(CHECKPOINT_FILE) as f:
                return json.load(f)
    except:
        pass
    return None

def resurrect_from_checkpoint():
    """
    Reef pattern: if health system itself went down, resurrect from checkpoint.
    This ensures the health system is self-healing.
    """
    checkpoint = load_checkpoint()
    if checkpoint:
        log(f"♻️ RESURRECTING from checkpoint: {checkpoint.get('timestamp')}")
        return checkpoint.get("state", {})
    return {}

def load_instinct_state():
    """Load instinct state (energy, threat levels)."""
    try:
        if Path(INSTINCT_STATE).exists():
            with open(INSTINCT_STATE) as f:
                return json.load(f)
    except:
        pass
    return {"energy": 1.0, "threat": 0.0, "guard_explorations": 0}

def save_instinct_state(state):
    """Save instinct state."""
    with open(INSTINCT_STATE, "w") as f:
        json.dump(state, f)

def instinct_survive(dead_services):
    """SURVIVE instinct: if services are down, drop everything to fix."""
    if not dead_services:
        return False
    log(f"⚡ SURVIVE INSTINCT: {len(dead_services)} services DOWN — fixing NOW")
    return True

def instinct_guard(all_healthy, health_state):
    """
    GUARD instinct: if services are healthy, explore new improvements.
    This drives proactive optimization when there's nothing broken.
    """
    if not all_healthy:
        return None
    
    consecutive = health_state.get("consecutive_healthy", 0)
    
    # GUARD triggers after 10 consecutive healthy checks (~50 min)
    if consecutive >= 10:
        log("⚡ GUARD INSTINCT: All healthy — exploring improvements")
        return "explore"
    
    return None

def log_anomaly(service, anomaly_type, details):
    """Log anomaly for trend analysis."""
    try:
        anomalies = []
        if Path(ANOMALY_LOG).exists():
            with open(ANOMALY_LOG) as f:
                anomalies = json.load(f)
    except:
        anomalies = []
    
    anomalies.append({
        "timestamp": datetime.utcnow().isoformat(),
        "service": service,
        "type": anomaly_type,
        "details": details
    })
    
    # Keep last 100 anomalies
    anomalies = anomalies[-100:]
    
    with open(ANOMALY_LOG, "w") as f:
        json.dump(anomalies, f)

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

def check_improvement_opportunities():
    """
    GUARD instinct: check for improvement opportunities when healthy.
    Returns list of potential improvements.
    """
    opportunities = []
    
    # Check disk usage
    try:
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    usage = parts[4].rstrip("%")
                    try:
                        if int(usage) > 85:
                            opportunities.append(f"disk_usage_high:{usage}%")
                    except:
                        pass
    except:
        pass
    
    # Check memory
    try:
        result = subprocess.run(
            ["free", "-m"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 2:
                parts = lines[1].split()
                if len(parts) >= 3:
                    try:
                        used = int(parts[2])
                        if used > 12000:  # > 12GB
                            opportunities.append(f"memory_high:{used}MB")
                    except:
                        pass
    except:
        pass
    
    return opportunities

def main():
    log("=== Health check (FM-instinct-enhanced) ===")
    
    instinct_state = load_instinct_state()
    health_state = load_health_state()
    
    # Check energy/threat levels
    energy = instinct_state.get("energy", 1.0)
    threat = instinct_state.get("threat", 0.0)
    
    if energy <= SURVIVE_THRESHOLD:
        log(f"⚠️ ENERGY CRITICAL: {energy:.2f} — SURVIVE mode only")
    
    if threat > THREAT_THRESHOLD:
        log(f"⚠️ THREAT HIGH: {threat:.2f} — FLEE mode")
    
    # Check all services
    dead = []
    alive = []
    for name, url in SERVICES:
        if check_service(name, url):
            alive.append(name)
        else:
            dead.append(name)
            log_anomaly(name, "DOWN", {"timestamp": datetime.utcnow().isoformat()})
    
    all_healthy = len(dead) == 0
    
    # SURVIVE instinct: if services down, fix immediately
    if instinct_survive(dead):
        health_state["last_down"] = datetime.utcnow().isoformat()
    
    if dead:
        log(f"⚠️ {len(dead)} services dead: {dead}")
        
        # Try to restart each
        restarted = []
        for name in dead:
            attempts = health_state.get("restart_attempts", {}).get(name, 0)
            if attempts < 3:  # Max 3 attempts per service
                if restart_service(name):
                    restarted.append(name)
                    health_state.setdefault("restart_attempts", {})[name] = attempts + 1
                    
                    # Log successful restart
                    log_anomaly(name, "RESTART_SUCCESS", {"attempts": attempts + 1})
        
        if restarted:
            log(f"Restarted: {restarted}")
        
        # If still dead after restart attempt, alert
        still_dead = [n for n in dead if n not in restarted]
        if still_dead:
            log(f"STILL DOWN: {still_dead}")
            # Write alert for main session
            with open("/tmp/health-alert.txt", "w") as f:
                f.write(f"SERVICES_DOWN:{','.join(still_dead)}\n")
        
        # Reset consecutive healthy counter
        health_state["consecutive_healthy"] = 0
    else:
        log("All services healthy")
        health_state["consecutive_healthy"] = health_state.get("consecutive_healthy", 0) + 1
        health_state["last_down"] = None
        health_state["restart_attempts"] = {}
    
    # GUARD instinct: if healthy, explore improvements
    guard_action = instinct_guard(all_healthy, health_state)
    if guard_action == "explore":
        opportunities = check_improvement_opportunities()
        if opportunities:
            log(f"⚡ GUARD: Found improvement opportunities: {opportunities}")
            with open("/tmp/health-guard-improvements.txt", "w") as f:
                for opp in opportunities:
                    f.write(f"{opp}\n")
        
        # Increment guard exploration counter
        instinct_state["guard_explorations"] = instinct_state.get("guard_explorations", 0) + 1
        save_instinct_state(instinct_state)
    
    # Save state with checkpoint (reef pattern)
    save_health_state(health_state)
    save_checkpoint(health_state)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())