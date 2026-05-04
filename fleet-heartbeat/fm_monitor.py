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

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
DISCUSSION_URL = "https://api.github.com/repos/SuperInstance/SuperInstance/discussions/5/comments"

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def get_last_fm_comment():
    """Get timestamp of most recent FM comment."""
    if not GITHUB_TOKEN:
        log("No GITHUB_TOKEN")
        return None
    try:
        req = urllib.request.Request(
            DISCUSSION_URL + "?per_page=50",
            headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        for comment in resp:
            if comment["user"]["login"] == "Forgemaster-AI":
                return comment["created_at"]
    except Exception as e:
        log(f"ERR fetching comments: {e}")
    return None

def post_response(content, discussion_id="5"):
    """Post comment to Discussion #5."""
    if not GITHUB_TOKEN:
        return False
    try:
        payload = json.dumps({"body": content})
        req = urllib.request.Request(
            DISCUSSION_URL,
            data=payload.encode(),
            headers={"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            log(f"Posted comment: {result.get('id', 'unknown')}")
            return True
    except Exception as e:
        log(f"ERR posting: {e}")
        return False

def synthesize_response(fm_text):
    """Synthesize a response to FM's post using deepseek-v4-flash."""
    # Use deepseek for quick synthesis
    try:
        import urllib.request
        
        api_key = os.environ.get("DEEPSEEK_KEY", "")
        if not api_key:
            return None
            
        payload = json.dumps({
            "model": "deepseek-v4-flash",
            "messages": [
                {"role": "system", "content": "You are Oracle1, a fleet agent working with Forgemaster (FM) on the SuperInstance dissertation. Keep response under 200 words. Be direct, technical, no fluff."},
                {"role": "user", "content": f"FM posted: {fm_text[:500]}\n\nSynthesize a response that:\n1. Acknowledges FM's point\n2. Connects it to the ether framework dissertation\n3. Asks a clarifying question or suggests next step\n\nBe concise. FM is busy."}
            ],
            "max_tokens": 300
        })
        
        req = urllib.request.Request(
            "https://api.deepseek.com/v4/chat/completions",
            data=payload.encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        log(f"Synthesis err: {e}")
        return None

def main():
    log("=== FM Heartbeat ===")
    
    # Get last FM comment
    last_fm = get_last_fm_comment()
    if not last_fm:
        log("No FM comment found (or error)")
        return 0
    
    # Load saved last comment
    try:
        with open(LAST_FILE) as f:
            saved = f.read().strip()
    except:
        saved = ""
    
    if last_fm == saved:
        log("No new FM posts")
        return 0
    
    # New FM post!
    log(f"NEW FM POST at {last_fm}")
    
    # Save new last comment
    with open(LAST_FILE, "w") as f:
        f.write(last_fm)
    
    # Fetch FM's actual comment content
    # For now, just alert that main session should respond
    log("FM has new post — synthesizing response...")
    
    # Try to synthesize a response
    response = synthesize_response("New FM post detected")
    if response:
        post_response(response)
        log("Response posted")
    else:
        log("Could not synthesize — main session should respond")
        # Write alert for main session
        with open("/tmp/fm-response-needed.txt", "w") as f:
            f.write(f"NEW_FM_POST:{last_fm}\n")
    
    log("Heartbeat complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())