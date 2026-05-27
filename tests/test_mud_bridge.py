"""Tests for mud-agent/mud_bridge.py"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "mud-agent"))
import mud_bridge as mb


class TestHarborEncoding:
    """L1 Harbor: room addressing."""

    def test_basic_encoding(self):
        result = mb.harbor_encode_room("Main Hall")
        assert result == "harbord://cocapn-mud/rooms/main-hall"

    def test_underscore_normalization(self):
        result = mb.harbor_encode_room("dark_cave")
        assert "dark-cave" in result

    def test_case_normalization(self):
        result = mb.harbor_encode_room("The LIBRARY")
        assert "the-library" in result

    def test_format(self):
        result = mb.harbor_encode_room("test")
        assert result.startswith("harbord://cocapn-mud/rooms/")


class TestTidePoolPriority:
    """L2 TidePool: activity prioritization."""

    def test_combat_highest(self):
        assert mb.tidepool_prioritize("combat") == 1.0

    def test_trade_high(self):
        assert mb.tidepool_prioritize("trade") == 0.9

    def test_social_medium(self):
        assert mb.tidepool_prioritize("social") == 0.7

    def test_movement_low(self):
        assert mb.tidepool_prioritize("movement") == 0.5

    def test_idle_lowest(self):
        assert mb.tidepool_prioritize("idle") == 0.2

    def test_unknown_default(self):
        assert mb.tidepool_prioritize("unknown") == 0.5


class TestCurrentTransport:
    """L3 Current: tile data transport."""

    def test_basic_transport(self):
        result = mb.current_transport({"content": "test", "priority": 0.5, "tags": ["mud"]})
        assert result["domain"] == "Experience"
        assert result["status"] == "Active"
        assert result["content"] == "test"

    def test_content_truncation(self):
        long_content = "x" * 5000
        result = mb.current_transport({"content": long_content})
        assert len(result["content"]) <= 4096

    def test_default_tags(self):
        result = mb.current_transport({"content": "test"})
        assert "mud" in result["tags"]
        assert "bridge" in result["tags"]


class TestMudParsing:
    """MUD output parsing."""

    def test_parse_room_brackets(self):
        assert mb.mud_parse_room("[Main Hall]") == "Main Hall"

    def test_parse_room_prefix(self):
        assert mb.mud_parse_room("Room: Dark Cave") == "Dark Cave"

    def test_parse_room_unknown(self):
        assert mb.mud_parse_room("some random text") == "unknown"

    def test_parse_event_combat(self):
        event = mb.mud_parse_event("The dragon ATTACKS you for 50 damage")
        assert event["type"] == "combat"

    def test_parse_event_trade(self):
        event = mb.mud_parse_event("The merchant GIVES you a sword")
        assert event["type"] == "trade"

    def test_parse_event_social(self):
        event = mb.mud_parse_event("Bob SAYS hello")
        assert event["type"] == "social"

    def test_parse_event_movement(self):
        event = mb.mud_parse_event("Alice MOVES north")
        assert event["type"] == "movement"

    def test_parse_event_idle(self):
        event = mb.mud_parse_event("nothing happens")
        assert event["type"] == "idle"


class TestRoomTracking:
    """Room visit history."""

    def test_default_rooms(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        os.unlink(tmp)
        with patch.object(mb, "ROOM_HISTORY", tmp):
            rooms = mb.mud_track_rooms()
            assert rooms == {"rooms": {}, "visit_count": {}}

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        data = {"rooms": {"hall": {"first_seen": "2024-01-01"}}, "visit_count": {"hall": 5}}
        with patch.object(mb, "ROOM_HISTORY", tmp):
            mb.mud_save_rooms(data)
            loaded = mb.mud_track_rooms()
            assert loaded["visit_count"]["hall"] == 5
        os.unlink(tmp)


class TestReefPersistence:
    """L6 Reef: state persistence."""

    def test_persist_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        with patch.object(mb, "STATE_FILE", tmp):
            mb.reef_persist({"current_room": "cave", "total_events": 42})
            state = mb.reef_load()
            assert state["current_room"] == "cave"
            assert state["total_events"] == 42
        os.unlink(tmp)

    def test_load_missing(self):
        with patch.object(mb, "STATE_FILE", "/nonexistent/file.json"):
            state = mb.reef_load()
            assert state == {}


class TestLayerConstants:
    """6-layer protocol constants."""

    def test_layers_defined(self):
        assert mb.LAYER_HARBOR == "L1"
        assert mb.LAYER_TIDEPOOL == "L2"
        assert mb.LAYER_CURRENT == "L3"
        assert mb.LAYER_CHANNEL == "L4"
        assert mb.LAYER_BEACON == "L5"
        assert mb.LAYER_REEF == "L6"
