#!/usr/bin/env python3
"""
ABOracle Fleet Heartbeat — FM coordination
Checks Discussion #5 every 30 min, responds autonomously
"""
import json, urllib.request, os, sys, subprocess
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/home/ubuntu/.openclaw/workspace")
LOG = "/tmp/aboracle-fm-heartbeat.log"
LAST_FILE = "/tmp/aboracle-fm-last-comment"

DISCUSSION_URL = "https://api.github.com/repos/SuperInstance/SuperInstance/discussions/5/comments"

def get_github_token():
    """Get GitHub token from bashrc or environment."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return token
    try:
        result = subprocess.run(
            ["grep", "^export GITHUB_TOKEN=", "/home/ubuntu/.bashrc"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout:
            token = result.stdout.split("=")[1].strip().strip('"').strip("'")
            return token
    except:
        pass
    return ""

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def get_last_fm_comment(token):
    if not token:
        log("No GITHUB_TOKEN found")
        return None
    try:
        req = urllib.request.Request(
            DISCUSSION_URL + "?per_page=50",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        for comment in resp:
            if comment["user"]["login"] == "Forgemaster-AI":
                return comment["created_at"]
    except Exception as e:
        log(f"ERR fetching comments: {e}")
    return None

def main():
    log("=== FM Heartbeat ===")
    token = get_github_token()
    if not token:
        log("ERROR: Cannot get GitHub token")
        return 1
    last_fm = get_last_fm_comment(token)
    if not last_fm:
        log("No FM comment found")
        return 0
    try:
        with open(LAST_FILE) as f:
            saved = f.read().strip()
    except:
        saved = ""
    if last_fm == saved:
        log("No new FM posts")
        return 0
    log(f"NEW FM POST at {last_fm}")
    with open(LAST_FILE, "w") as f:
        f.write(last_fm)
    with open("/tmp/fm-response-needed.txt", "w") as f:
        f.write(f"NEW_FM_POST:{last_fm}\n")
    log("Heartbeat complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())