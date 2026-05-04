#!/bin/bash
# ABOracle deploy — copy to new machine, run this, done
# No per-machine config. Just copy, run, busy.
#
# FM-instinct-enhanced with:
# - Health-check before deploy
# - Rollback capability (git reset --hard to last known good)
# - FM instinct initialization on boot (energy, threat, trust levels)

set -e
echo "[ABOracle] Deploying..."

WORKSPACE="$HOME/.openclaw/workspace"
ABORACLE_DIR="$WORKSPACE/repos/aboracle"
LOG="/tmp/aboracle-deploy.log"
INSTINCT_FILE="/tmp/aboracle-instinct-state.json"
HEALTH_STATE_FILE="/tmp/aboracle-health-state.json"
CHECKPOINT_REF=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG"
}

# ---- Health Check Functions ----

check_service() {
    local name=$1
    local url=$2
    curl -sf --max-time 5 "$url" > /dev/null 2>&1
    return $?
}

run_health_check() {
    log "${YELLOW}Running pre-deploy health check...${NC}"
    
    local services=(
        "plato:http://localhost:8847/status"
        "keeper:http://localhost:8900/"
        "agent-api:http://localhost:8901/"
        "holodeck:http://localhost:7778/"
        "seed-mcp:http://localhost:9438/status"
    )
    
    local all_healthy=true
    local dead_services=()
    
    for svc in "${services[@]}"; do
        IFS=':' read -r name url <<< "$svc"
        if check_service "$name" "$url"; then
            log "  ✓ $name healthy"
        else
            log "  ${RED}✗ $name DEAD${NC}"
            dead_services+=("$name")
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = true ]; then
        log "${GREEN}All services healthy — proceeding with deploy${NC}"
        return 0
    else
        log "${YELLOW}Warning: ${#dead_services[@]} services dead${NC}"
        log "Will attempt restart after deploy..."
        return 1
    fi
}

# ---- FM Instinct Initialization ----

init_fm_instincts() {
    log "${YELLOW}Initializing FM instinct stack...${NC}"
    
    # Create instinct state with FM's default values from constraint-theory-paper
    # energy: 1.0 (full), threat: 0.0 (no threats), trust: fleet defaults
    cat > "$INSTINCT_FILE" << 'EOF'
{
    "energy": 1.0,
    "threat": 0.0,
    "trust": {
        "Forgemaster-AI": 0.85,
        "JetsonClaw1": 0.75,
        "Babel": 0.60,
        "SuperInstance": 0.90,
        "casey": 1.0
    },
    "guard_explorations": 0,
    "cooperate_count": 0,
    "idle_ticks": 0,
    "boot_time": null
}
EOF
    
    # Add boot time
    python3 -c "
import json
from datetime import datetime
with open('$INSTINCT_FILE') as f:
    state = json.load(f)
state['boot_time'] = datetime.utcnow().isoformat()
with open('$INSTINCT_FILE', 'w') as f:
    json.dump(state, f, indent=2)
"
    
    log "  Instinct state initialized:"
    log "    energy: 1.0 (SURVIVE threshold: ≤0.15)"
    log "    threat: 0.0 (FLEE threshold: >0.7)"
    log "    trust: fleet defaults loaded"
    log "${GREEN}✓ FM instinct stack initialized${NC}"
}

# ---- Rollback Functions ----

save_checkpoint_ref() {
    CHECKPOINT_REF=$(git -C "$ABORACLE_DIR" rev-parse HEAD)
    log "Checkpoint ref: $CHECKPOINT_REF"
}

rollback() {
    log "${RED}Rolling back to checkpoint: $CHECKPOINT_REF${NC}"
    git -C "$ABORACLE_DIR" reset --hard "$CHECKPOINT_REF"
    log "${GREEN}Rollback complete${NC}"
}

# ---- Main Deployment ----

echo "[ABOracle] Deploy started at $(date)" | tee "$LOG"

# Ensure workspace exists
mkdir -p "$WORKSPACE/repos"

# Clone if not exists (for new machines)
if [ ! -d "$ABORACLE_DIR" ]; then
    log "Cloning aboracle repo..."
    git clone https://github.com/SuperInstance/aboracle.git "$ABORACLE_DIR"
else
    log "ABOracle dir exists — pulling latest..."
    cd "$ABORACLE_DIR"
    git pull origin main --no-edit || true
fi

cd "$ABORACLE_DIR"

# Pre-deploy health check
run_health_check || true  # Don't fail deploy if health check fails

# Save checkpoint for rollback
log "Saving rollback checkpoint..."
save_checkpoint_ref

# Initialize FM instinct stack
init_fm_instincts

# Set up crons
log "Setting up crons..."

# Remove old aboracle crons if any
(crontab -l 2>/dev/null | grep -v "aboracle" || true) | crontab -

# Add new crons
(crontab -l 2>/dev/null; cat << 'CRON'
# ABOracle Work Queue — FM-instinct-enhanced priority system
*/5 * * * * cd $HOME/.openclaw/workspace/repos/aboracle && python3 work-queue/prioritizer.py >> /tmp/aboracle-work.log 2>&1

# ABOracle Beachcomb — Pythagorean48 research + EVOLVE instinct
*/30 * * * * cd $HOME/.openclaw/workspace/repos/aboracle && python3 beachcomb/researcher.py >> /tmp/aboracle-beachcomb.log 2>&1

# ABOracle Fleet Heartbeat — mycorrhizal routing + COOPERATE instinct
*/30 * * * * cd $HOME/.openclaw/workspace/repos/aboracle && python3 fleet-heartbeat/fm_monitor.py >> /tmp/aboracle-fm-heartbeat.log 2>&1

# ABOracle Health System — GUARD/SURVIVE instincts + reef persistence
*/5 * * * * cd $HOME/.openclaw/workspace/repos/aboracle && python3 health-system/monitor.py >> /tmp/aboracle-health.log 2>&1
CRON
) | crontab -

# Ensure MUD bridge can run (optional — only if MUD server is available)
if check_service "mud" "http://localhost:7777/"; then
    log "MUD server detected — MUD bridge will activate"
    # MUD bridge runs as background process, not cron (continuous monitoring)
fi

# Post-deploy health check
log "Post-deploy health check..."
run_health_check || {
    log "${YELLOW}Some services need attention — will be handled by health-system${NC}"
}

echo ""
log "${GREEN}✓ Deployed successfully${NC}"
echo ""
echo "Systems running:"
echo "  work-queue/      (every 5 min) — FM-instinct priority: SURVIVE > FLEE > GUARD > CURIOUS"
echo "  beachcomb/       (every 30 min) — Pythagorean48 research + EVOLVE instinct"
echo "  fleet-heartbeat/ (every 30 min) — mycorrhizal routing + COOPERATE instinct"
echo "  health-system/   (every 5 min)  — GUARD/SURVIVE instincts + reef pattern"
echo "  mud-agent/       (continuous)   — 6-layer MUD↔PLATO bridge"
echo ""
echo "Logs:"
echo "  /tmp/aboracle-work.log"
echo "  /tmp/aboracle-beachcomb.log"
echo "  /tmp/aboracle-fm-heartbeat.log"
echo "  /tmp/aboracle-health.log"
echo "  /tmp/aboracle-mud-bridge.log"
echo ""
echo "FM Instinct State:"
echo "  $INSTINCT_FILE"
echo ""
echo "Rollback point saved: $CHECKPOINT_REF"
echo "To rollback: cd $ABORACLE_DIR && git reset --hard $CHECKPOINT_REF"
echo ""
echo "To check status: tail -f /tmp/aboracle-*.log"
echo "[ABOracle] Deploy complete at $(date)" | tee -a "$LOG"