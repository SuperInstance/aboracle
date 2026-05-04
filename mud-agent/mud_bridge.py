#!/usr/bin/env python3
"""
ABOracle MUD Agent — bridges text-MUD world and PLATO knowledge world
Uses FM's 6-layer ship protocol:
  - Harbor (L1): room navigation and addressing
  - TidePool (L2): trust-weighted message prioritization
  - Current (L3): tile export/import/transport
  - Channel (L4): MUD↔PLATO bridging
  - Beacon (L5): trust event propagation
  - Reef (L6): state handoff and persistence

Watches MUD room activity, posts summaries to PLATO.
Fully async, runs as background monitor.

Usage: python3 mud-agent/mud_bridge.py
"""
import json, urllib.request, socket, select, re, sys, time
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/home/ubuntu/.openclaw/workspace")
PLATO = "http://localhost:8847"
LOG = "/tmp/aboracle-mud-bridge.log"
STATE_FILE = "/tmp/aboracle-mud-state.json"
ACTIVITY_LOG = "/tmp/aboracle-mud-activity.json"
ROOM_HISTORY = "/tmp/aboracle-mud-rooms.json"

# MUD connection settings
MUD_HOST = "localhost"
MUD_PORT = 7777
MUD_TIMEOUT = 5  # seconds

# 6-Layer Protocol layer names
LAYER_HARBOR   = "L1"   # Room addressing
LAYER_TIDEPOOL = "L2"   # Trust-weighted prioritization
LAYER_CURRENT  = "L3"   # Tile transport
LAYER_CHANNEL  = "L4"   # MUD↔PLATO bridge
LAYER_BEACON   = "L5"   # Trust events
LAYER_REEF     = "L6"   # State persistence

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] [MUD-BRIDGE] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

# ---- 6-Layer Protocol Helpers ----

def harbor_encode_room(room_name):
    """
    L1 Harbor: encode room name to canonical address.
    Format: harbord://realm/zone/room
    """
    # Normalize room name to address
    normalized = room_name.lower().replace(" ", "-").replace("_", "-")
    return f"harbord://cocapn-mud/rooms/{normalized}"

def tidepool_prioritize(activity_type):
    """
    L2 TidePool: trust-weighted message prioritization.
    Higher priority events get processed first.
    """
    priorities = {
        "combat": 1.0,      # Highest
        "trade": 0.9,
        "social": 0.7,
        "movement": 0.5,
        "idle": 0.2,        # Lowest
    }
    return priorities.get(activity_type, 0.5)

def current_transport(tile_data):
    """
    L3 Current: transport tile data to/from MUD world.
    Converts MUD events to PLATO tile format.
    """
    return {
        "domain": "Experience",
        "status": "Active",
        "content": tile_data.get("content", "")[:4096],
        "weight": tile_data.get("priority", 0.5),
        "belief": 0.8,
        "tags": tile_data.get("tags", ["mud", "bridge"]),
    }

def channel_bridge(mud_event, mud_room):
    """
    L4 Channel: bridge MUD event to PLATO knowledge world.
    Returns True if successfully bridged.
    """
    try:
        # Post to PLATO room oracle_mud_events
        room = "oracle_mud_events"
        tile = {
            "content": f"[{mud_event.get('type', 'unknown')}] {mud_event.get('text', '')}",
            "tags": ["mud", mud_event.get("type", "event"), mud_room],
            "weight": tidepool_prioritize(mud_event.get("type", "idle")),
        }
        
        # Use PLATO API if available
        try:
            req = urllib.request.Request(
                f"{PLATO}/room/{room}/tile",
                data=json.dumps(tile).encode(),
                headers={"Content-Type": "application/json", "User-Agent": "aboracle-mud"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5):
                return True
        except:
            pass
        
        # Fallback: write to activity file for main session to process
        with open(ACTIVITY_LOG, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "room": mud_room,
                "event": mud_event,
                "layer": LAYER_CHANNEL
            }) + "\n")
        return True
    except Exception as e:
        log(f"Channel bridge error: {e}")
        return False

def beacon_emit(trust_event):
    """
    L5 Beacon: propagate trust events.
    Notifies other systems of MUD-related trust signals.
    """
    log(f"BEACON: {trust_event}")

def reef_persist(state):
    """
    L6 Reef: persist state for handoff/resurrection.
    Ensures continuity across restarts.
    """
    with open(STATE_FILE, "w") as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "state": state,
            "version": "1.0"
        }, f)

def reef_load():
    """Load persisted state."""
    try:
        if Path(STATE_FILE).exists():
            with open(STATE_FILE) as f:
                data = json.load(f)
                return data.get("state", {})
    except:
        pass
    return {}

# ---- MUD Protocol ----

def mud_connect():
    """Connect to MUD server."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(MUD_TIMEOUT)
        sock.connect((MUD_HOST, MUD_PORT))
        log(f"Connected to MUD at {MUD_HOST}:{MUD_PORT}")
        return sock
    except Exception as e:
        log(f"MUD connection failed: {e}")
        return None

def mud_read_line(sock):
    """Read one line from MUD (non-blocking)."""
    sock.setblocking(0)
    ready, _, _ = select.select([sock], [], [], 0.1)
    if ready:
        try:
            data = sock.recv(4096).decode("utf-8", errors="ignore")
            return data
        except:
            pass
    return ""

def mud_parse_room(text):
    """Extract room name from MUD output."""
    # Common room patterns
    patterns = [
        r"^\[(.*?)\]$",           # [RoomName]
        r"^Room:\s*(.*?)$",       # Room: Name
        r"^\*\*?(.*?)\*\*?:$",     # **RoomName**:
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return match.group(1).strip()
    return "unknown"

def mud_parse_event(text):
    """Parse MUD event type from text."""
    text_upper = text.upper()
    if any(kw in text_upper for kw in ["ATTACKS", "KILLS", "COMBAT", "DAMAGE"]):
        return {"type": "combat", "text": text}
    elif any(kw in text_upper for kw in ["GIVES", "TRADES", "SELLS", "BUYS"]):
        return {"type": "trade", "text": text}
    elif any(kw in text_upper for kw in ["SAYS", "TELLS", "SHOUTS", "SOCIAL"]):
        return {"type": "social", "text": text}
    elif any(kw in text_upper for kw in ["MOVES", "GOES", "ENTERS", "EXITS"]):
        return {"type": "movement", "text": text}
    return {"type": "idle", "text": text}

def mud_track_rooms():
    """Track room visit history."""
    try:
        if Path(ROOM_HISTORY).exists():
            with open(ROOM_HISTORY) as f:
                return json.load(f)
    except:
        pass
    return {"rooms": {}, "visit_count": {}}

def mud_save_rooms(rooms):
    """Save room history."""
    with open(ROOM_HISTORY, "w") as f:
        json.dump(rooms, f)

def mud_summarize_activity():
    """
    Summarize recent MUD activity and post to PLATO.
    Called periodically, not on every event.
    """
    rooms = mud_track_rooms()
    
    if not rooms.get("visit_count"):
        return
    
    # Find most visited rooms
    sorted_rooms = sorted(rooms["visit_count"].items(), key=lambda x: x[1], reverse=True)
    top_rooms = sorted_rooms[:5]
    
    summary = f"MUD Activity Summary (last cycle):\n"
    for room, count in top_rooms:
        summary += f"- {room}: {count} visits\n"
    
    log(f"Activity summary: {len(top_rooms)} active rooms")
    
    # Post to PLATO via channel bridge
    event = {"type": "summary", "text": summary}
    channel_bridge(event, "activity-summary")

# ---- Main Loop ----

def main():
    log("=== MUD Bridge Agent (6-layer protocol) ===")
    
    state = reef_load()
    sock = None
    reconnect_delay = 5
    last_summary_time = time.time()
    lines_since_room = 0
    current_room = "unknown"
    
    while True:
        try:
            # Reconnect if needed
            if sock is None:
                sock = mud_connect()
                if sock is None:
                    log(f"Reconnecting in {reconnect_delay}s...")
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 60)
                    continue
                else:
                    reconnect_delay = 5
            
            # Read MUD output
            data = mud_read_line(sock)
            if data:
                lines = data.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse room changes
                    room = mud_parse_room(line)
                    if room != current_room:
                        current_room = room
                        lines_since_room = 0
                        
                        # L1 Harbor: track room address
                        harbor_addr = harbor_encode_room(room)
                        log(f"Harbor: {harbor_addr}")
                        
                        # Update room history
                        rooms = mud_track_rooms()
                        rooms.setdefault("rooms", {})[room] = {
                            "first_seen": datetime.utcnow().isoformat(),
                            "address": harbor_addr,
                        }
                        rooms.setdefault("visit_count", {})[room] = rooms["visit_count"].get(room, 0) + 1
                        mud_save_rooms(rooms)
                        reef_persist({"current_room": room, "total_events": state.get("total_events", 0) + 1})
                    else:
                        lines_since_room += 1
                    
                    # Parse event type
                    event = mud_parse_event(line)
                    
                    # L2 TidePool: check if worth bridging
                    priority = tidepool_prioritize(event["type"])
                    if priority < 0.3:
                        continue  # Skip low-priority idle events
                    
                    # L4 Channel: bridge to PLATO
                    if channel_bridge(event, current_room):
                        log(f"Channel: bridged {event['type']} from {current_room}")
                    
                    # L5 Beacon: emit high-priority trust events
                    if event["type"] in ["combat", "trade"]:
                        beacon_emit({"type": event["type"], "room": current_room, "layer": LAYER_BEACON})
                    
                    state["total_events"] = state.get("total_events", 0) + 1
            
            # Periodic activity summary (every 5 min)
            if time.time() - last_summary_time > 300:
                mud_summarize_activity()
                last_summary_time = time.time()
            
            # Reef: persist state periodically
            if state.get("total_events", 0) % 50 == 0:
                reef_persist(state)
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            log("Shutting down MUD bridge")
            break
        except Exception as e:
            log(f"Error: {e}")
            if sock:
                try:
                    sock.close()
                except:
                    pass
            sock = None
            time.sleep(reconnect_delay)
    
    if sock:
        sock.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())