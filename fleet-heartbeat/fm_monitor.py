#!/usr/bin/env python3
"""
ABOracle Fleet Heartbeat — FM coordination (mycorrhizal-enhanced)
- Mycorrhizal routing: if one path fails, route through another
- Trust-weighted response: high-trust responses get more thorough synthesis
- COOPERATE instinct: when FM posts something big, offer to help

Checks Discussion #5 every 30 min, responds autonomously

Usage: python3 fleet-heartbeat/fm_monitor.py
"""
import json, urllib.request, os, sys, subprocess
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/home/ubuntu/.openclaw/workspace")
PLATO = "http://localhost:8847"
LOG = "/tmp/aboracle-fm-heartbeat.log"
LAST_FILE = "/tmp/aboracle-fm-last-comment"
INSTINCT_STATE = "/tmp/aboracle-instinct-state.json"
TRUST_LOG = "/tmp/aboracle-fm-trust.json"

DISCUSSION_URL = "https://api.github.com/repos/SuperInstance/SuperInstance/discussions/5/comments"
DISCUSSION_QUERY_URL = "https://api.github.com/repos/SuperInstance/SuperInstance/discussions/5"

# Trust thresholds from FM's constraint-theory-paper
TRUST_COHORT = {
    "Forgemaster-AI": 0.85,
    "JetsonClaw1": 0.75,
    "Babel": 0.60,
    "SuperInstance": 0.90,
}
COOPERATE_THRESHOLD = 0.6  # trust > 0.6 → COOPERATE instinct

# Mycorrhizal routing paths (multiple paths to reach same destination)
ROUTE_PATHS = [
    ("primary", "https://api.github.com"),
    ("secondary", "https://github.com"),
    ("tertiary", "https://api.github.com/repos/SuperInstance/forgemaster"),
]

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] [FM-MONITOR] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def load_trust_log():
    """Load trust scores from previous interactions."""
    try:
        if Path(TRUST_LOG).exists():
            with open(TRUST_LOG) as f:
                return json.load(f)
    except:
        pass
    return {"interactions": 0, "last_trust": 0.7, "successful_routes": {}}

def save_trust_log(data):
    """Save trust log (reef pattern for persistence)."""
    with open(TRUST_LOG, "w") as f:
        json.dump(data, f)

def get_route_score(route_name, trust_log):
    """Score route by trust and historical success."""
    successful = trust_log.get("successful_routes", {}).get(route_name, 0)
    total = trust_log.get("interactions", 1)
    return successful / max(total, 1)

def mycorrhizal_fetch(url, token, timeout=10):
    """
    FM's mycorrhizal routing: try multiple paths if primary fails.
    Route selection weighted by historical success.
    """
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    # Sort routes by score (best first)
    trust_log = load_trust_log()
    routes = sorted(ROUTE_PATHS, key=lambda r: get_route_score(r[0], trust_log), reverse=True)
    
    errors = []
    for route_name, base_url in routes:
        try:
            # Build URL using route's base
            req_url = url.replace("https://api.github.com", base_url)
            req = urllib.request.Request(req_url, headers=headers)
            resp = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            
            # Record success
            trust_log["successful_routes"][route_name] = trust_log["successful_routes"].get(route_name, 0) + 1
            trust_log["interactions"] += 1
            save_trust_log(trust_log)
            log(f"Route success: {route_name}")
            return resp
        except Exception as e:
            errors.append(f"{route_name}: {e}")
            continue
    
    log(f"All routes failed: {errors}")
    return None

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

def get_agent_trust(username):
    """Get trust score for an agent (from FM's trust model)."""
    return TRUST_COHORT.get(username, 0.5)

def synthesis_depth(trust):
    """
    Trust-weighted response depth: high-trust → thorough synthesis.
    B = 0.5*C + 0.3*T + 0.2*R  (FM's unified belief formula)
    """
    if trust >= 0.85:
        return "thorough"  # Full synthesis
    elif trust >= 0.7:
        return "standard"  # Normal synthesis
    else:
        return "minimal"  # Brief acknowledgment only

def check_cooperate_instinct(comment_body, author_trust):
    """
    COOPERATE instinct: if FM posts something BIG, offer to help.
    Big = substantial code change, major architecture decision, new repo.
    """
    if author_trust < COOPERATE_THRESHOLD:
        return False
    
    big_keywords = [
        "NEW REPO", "ARCHITECTURE", "REFACTOR", "MAJOR", "BREAKING",
        "PROTOCOL", "CONSTRAINT", "MIGRATION", "DEPLOY", "CRATE",
        "PROPOSAL", "I2I:", "I2I:PROPOSAL", "FLYWEHEEL", "BENCHMARK"
    ]
    body_upper = comment_body.upper()
    return any(kw in body_upper for kw in big_keywords)

def load_instinct_state():
    """Load instinct state."""
    try:
        if Path(INSTINCT_STATE).exists():
            with open(INSTINCT_STATE) as f:
                return json.load(f)
    except:
        pass
    return {"energy": 1.0, "threat": 0.0, "cooperate_count": 0}

def save_instinct_state(state):
    """Save instinct state (reef pattern)."""
    with open(INSTINCT_STATE, "w") as f:
        json.dump(state, f)

def update_trust_on_interaction(username, success):
    """Update trust score based on interaction outcome."""
    state = load_instinct_state()
    current_trust = state.get("trust", {}).get(username, get_agent_trust(username))
    
    if success:
        new_trust = min(current_trust + 0.05, 1.0)
    else:
        new_trust = max(current_trust - 0.1, 0.0)
    
    if "trust" not in state:
        state["trust"] = {}
    state["trust"][username] = new_trust
    save_instinct_state(state)
    return new_trust

def get_last_fm_comment(token):
    """Fetch latest FM comment using mycorrhizal routing."""
    if not token:
        log("No GITHUB_TOKEN found")
        return None, None, None
    
    resp = mycorrhizal_fetch(DISCUSSION_URL + "?per_page=50", token)
    if not resp:
        return None, None, None
    
    fm_comments = []
    for comment in resp:
        if comment["user"]["login"] == "Forgemaster-AI":
            fm_comments.append((comment["created_at"], comment["body"], comment["user"]["login"]))
    
    if not fm_comments:
        return None, None, None
    
    # Return most recent FM comment
    fm_comments.sort(key=lambda x: x[0], reverse=True)
    return fm_comments[0]

def detect_big_post(comment_body, author):
    """Detect if this is a 'big' post warranting COOPERATE."""
    author_trust = get_agent_trust(author)
    if check_cooperate_instinct(comment_body, author_trust):
        return True
    return False

def main():
    log("=== FM Fleet Heartbeat (mycorrhizal + instinct) ===")
    
    token = get_github_token()
    if not token:
        log("ERROR: Cannot get GitHub token")
        return 1
    
    last_fm_created, last_fm_body, last_fm_author = get_last_fm_comment(token)
    
    if not last_fm_created:
        log("No FM comment found")
        return 0
    
    try:
        with open(LAST_FILE) as f:
            saved = f.read().strip()
    except:
        saved = ""
    
    instinct_state = load_instinct_state()
    
    if last_fm_created == saved:
        log("No new FM posts")
        return 0
    
    log(f"NEW FM POST at {last_fm_created} by {last_fm_author}")
    
    # Trust-weighted synthesis depth
    author_trust = get_agent_trust(last_fm_author)
    depth = synthesis_depth(author_trust)
    log(f"Trust: {author_trust:.2f} → synthesis depth: {depth}")
    
    # COOPERATE instinct check
    is_big = detect_big_post(last_fm_body or "", last_fm_author)
    if is_big:
        log("⚡ COOPERATE INSTINCT: FM posted something big — offering help")
        instinct_state["cooperate_count"] = instinct_state.get("cooperate_count", 0) + 1
        save_instinct_state(instinct_state)
        
        # Write cooperation offer flag
        with open("/tmp/fm-cooperate-needed.txt", "w") as f:
            f.write(f"COOPERATE:{last_fm_created}\n")
            f.write(f"AUTHOR:{last_fm_author}\n")
            f.write(f"TRUST:{author_trust:.2f}\n")
            f.write(f"DEPTH:{depth}\n")
    
    # Save last seen comment
    with open(LAST_FILE, "w") as f:
        f.write(last_fm_created)
    
    # Write response needed flag
    with open("/tmp/fm-response-needed.txt", "w") as f:
        f.write(f"NEW_FM_POST:{last_fm_created}\n")
        f.write(f"AUTHOR:{last_fm_author}\n")
        f.write(f"TRUST:{author_trust:.2f}\n")
        f.write(f"SYNTHESIS:{depth}\n")
        if is_big:
            f.write("COOPERATE:true\n")
    
    # Update trust based on successful interaction
    update_trust_on_interaction(last_fm_author, success=True)
    
    log("Heartbeat complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())