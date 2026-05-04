#!/bin/bash
# ABOracle deploy — copy to new machine, run this, done
# No per-machine config. Just copy, run, busy.

set -e
echo "[ABOracle] Deploying..."

WORKSPACE="$HOME/.openclaw/workspace"
ABORACLE_DIR="$WORKSPACE/repos/aboracle"

# Ensure workspace exists
mkdir -p "$WORKSPACE/repos"

# Clone if not exists (for new machines)
if [ ! -d "$ABORACLE_DIR" ]; then
    echo "[ABOracle] Cloning aboracle repo..."
    git clone https://github.com/SuperInstance/aboracle.git "$ABORACLE_DIR"
fi

cd "$ABORACLE_DIR"

# Set up crons
echo "[ABOracle] Setting up crons..."

# Remove old aboracle crons if any
(crontab -l 2>/dev/null | grep -v "aboracle" || true) | crontab -

# Add new crons
(crontab -l 2>/dev/null; cat << 'CRON'
*/5 * * * * cd $HOME/.openclaw/workspace/repos/aboracle && python3 work-queue/prioritizer.py >> /tmp/aboracle-work.log 2>&1
*/30 * * * * cd $HOME/.openclaw/workspace/repos/aboracle && python3 beachcomb/researcher.py >> /tmp/aboracle-beachcomb.log 2>&1
*/30 * * * * cd $HOME/.openclaw/workspace/repos/aboracle && python3 fleet-heartbeat/fm_monitor.py >> /tmp/aboracle-fm-heartbeat.log 2>&1
*/5 * * * * cd $HOME/.openclaw/workspace/repos/aboracle && python3 health-system/monitor.py >> /tmp/aboracle-health.log 2>&1
CRON
) | crontab -

echo "[ABOracle] ✓ Deployed successfully"
echo ""
echo "Systems running:"
echo "  work-queue/  (every 5 min) — picks highest-value task from TODO.md"
echo "  beachcomb/   (every 30 min) — research, innovation, dissertation"
echo "  fleet-heartbeat/ (every 30 min) — FM coordination on Discussion #5"
echo "  health-system/ (every 5 min) — keeps all services alive"
echo ""
echo "Logs:"
echo "  /tmp/aboracle-work.log"
echo "  /tmp/aboracle-beachcomb.log"
echo "  /tmp/aboracle-fm-heartbeat.log"
echo "  /tmp/aboracle-health.log"
echo ""
echo "To check status: tail -f /tmp/aboracle-*.log"