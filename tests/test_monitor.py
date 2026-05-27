"""Tests for health-system/monitor.py"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "health-system"))
import monitor as mon


class TestHealthState:
    """Health state persistence (reef pattern)."""

    def test_default_state(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        os.unlink(tmp)
        with patch.object(mon, "HEALTH_STATE_FILE", tmp):
            state = mon.load_health_state()
            assert state["consecutive_healthy"] == 0
            assert state["restart_attempts"] == {}

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write('{"consecutive_healthy": 5, "last_down": null, "restart_attempts": {}}')
            tmp = f.name
        with patch.object(mon, "HEALTH_STATE_FILE", tmp):
            state = mon.load_health_state()
            assert state["consecutive_healthy"] == 5
            mon.save_health_state({"consecutive_healthy": 10, "last_down": None, "restart_attempts": {}})
            assert mon.load_health_state()["consecutive_healthy"] == 10
        os.unlink(tmp)


class TestCheckpoint:
    """Reef pattern checkpoint save/load."""

    def test_save_checkpoint(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        with patch.object(mon, "CHECKPOINT_FILE", tmp):
            mon.save_checkpoint({"consecutive_healthy": 3})
            loaded = mon.load_checkpoint()
            assert loaded["state"]["consecutive_healthy"] == 3
            assert loaded["version"] == "1.0"
            assert "timestamp" in loaded

    def test_load_missing_checkpoint(self):
        with patch.object(mon, "CHECKPOINT_FILE", "/nonexistent/file.json"):
            assert mon.load_checkpoint() is None


class TestInstinctSurvive:
    """SURVIVE instinct triggers."""

    def test_triggers_on_dead_services(self):
        assert mon.instinct_survive(["plato"]) is True

    def test_no_trigger_when_healthy(self):
        assert mon.instinct_survive([]) is False


class TestInstinctGuard:
    """GUARD instinct triggers."""

    def test_triggers_after_consecutive_healthy(self):
        state = {"consecutive_healthy": 10}
        assert mon.instinct_guard(True, state) == "explore"

    def test_no_trigger_below_threshold(self):
        state = {"consecutive_healthy": 5}
        assert mon.instinct_guard(True, state) is None

    def test_no_trigger_when_unhealthy(self):
        state = {"consecutive_healthy": 15}
        assert mon.instinct_guard(False, state) is None


class TestAnomalyLogging:
    """Anomaly tracking."""

    def test_log_anomaly(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        with patch.object(mon, "ANOMALY_LOG", tmp):
            mon.log_anomaly("plato", "DOWN", {"timestamp": "2024-01-01"})
            with open(tmp) as f:
                anomalies = json.load(f)
            assert len(anomalies) == 1
            assert anomalies[0]["service"] == "plato"

    def test_anomaly_log_truncation(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        with patch.object(mon, "ANOMALY_LOG", tmp):
            for i in range(150):
                mon.log_anomaly("svc", "test", {"i": i})
            with open(tmp) as f:
                anomalies = json.load(f)
            assert len(anomalies) == 100  # capped at 100


class TestResurrection:
    """Reef pattern resurrection."""

    def test_resurrect_from_checkpoint(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"timestamp": "2024-01-01", "state": {"consecutive_healthy": 42}, "version": "1.0"}, f)
            tmp = f.name
        with patch.object(mon, "CHECKPOINT_FILE", tmp):
            state = mon.resurrect_from_checkpoint()
            assert state["consecutive_healthy"] == 42
        os.unlink(tmp)
