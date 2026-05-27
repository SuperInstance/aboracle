"""Integration tests verifying cross-module behavior."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import all modules
sys.path.insert(0, str(Path(__file__).parent.parent / "work-queue"))
sys.path.insert(0, str(Path(__file__).parent.parent / "beachcomb"))
sys.paths = sys.path  # already set
import prioritizer as pq
sys.path.insert(0, str(Path(__file__).parent.parent / "beachcomb"))
import researcher as rc
sys.path.insert(0, str(Path(__file__).parent.parent / "health-system"))
import monitor as mon
sys.path.insert(0, str(Path(__file__).parent.parent / "fleet-heartbeat"))
import fm_monitor as fm
sys.path.insert(0, str(Path(__file__).parent.parent / "mud-agent"))
import mud_bridge as mb


class TestInstinctConsistency:
    """All modules should respect the same instinct thresholds."""

    def test_survive_threshold(self):
        assert pq.BAND_SURVIVE == 0
        assert mon.SURVIVE_THRESHOLD == 0.15

    def test_threat_threshold(self):
        assert mon.THREAT_THRESHOLD == 0.7


class TestEndToEndFlow:
    """Simulate a complete instinct-driven cycle."""

    def test_low_energy_only_survive_tasks(self):
        """When energy is low, only SURVIVE-band tasks should be selected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            todo_path = Path(tmpdir) / "TODO.md"
            todo_path.write_text(
                "- [ ] CRITICAL service is DOWN\n"
                "- [ ] normal task P1\n"
                "- [ ] research explore ideas\n"
            )
            credits_path = Path(tmpdir) / "credits.json"
            credits_path.write_text('{"api_credits": 10.0, "memory_pct": 0.5}')  # 10%

            instinct_path = Path(tmpdir) / "instinct.json"
            instinct_path.write_text('{"energy": 0.1, "threat": 0.0, "trust": {}}')

            with patch.object(pq, "TODO_PATH", todo_path), \
                 patch.object(pq, "CREDITS_FILE", str(credits_path)), \
                 patch.object(pq, "INSTINCT_STATE", str(instinct_path)):
                band, source, text = pq.next_task()
                assert band == pq.BAND_SURVIVE
                assert "DOWN" in text

    def test_healthy_system_guard_mode(self):
        """When healthy, guard tasks should be selected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            todo_path = Path(tmpdir) / "TODO.md"
            todo_path.write_text("- [ ] implement feature X\n")

            credits_path = Path(tmpdir) / "credits.json"
            credits_path.write_text('{"api_credits": 100.0, "memory_pct": 0.5}')

            instinct_path = Path(tmpdir) / "instinct.json"
            instinct_path.write_text('{"energy": 1.0, "threat": 0.0, "trust": {}}')

            with patch.object(pq, "TODO_PATH", todo_path), \
                 patch.object(pq, "CREDITS_FILE", str(credits_path)), \
                 patch.object(pq, "INSTINCT_STATE", str(instinct_path)):
                band, source, text = pq.next_task()
                assert band == pq.BAND_GUARD

    def test_mud_event_to_plato_bridge(self):
        """MUD events should be transportable to PLATO format."""
        event = mb.mud_parse_event("Dragon ATTACKS for 50 damage")
        assert event["type"] == "combat"

        tile = mb.current_transport({
            "content": event["text"],
            "priority": mb.tidepool_prioritize(event["type"]),
            "tags": ["mud", event["type"]],
        })
        assert tile["content"] == "Dragon ATTACKS for 50 damage"
        assert tile["weight"] == 1.0

    def test_research_note_round_trip(self):
        """Research notes should survive encoding/decoding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(rc, "NOTES_DIR", Path(tmpdir)):
                triple = rc.save_research_note("test", "sample research content")
                files = list(Path(tmpdir).glob("*.md"))
                assert len(files) == 1

                # Read back and verify holonomy
                content = files[0].read_text()
                assert "pythagorean48:" in content
                assert triple in content
