"""Tests for fleet-heartbeat/fm_monitor.py"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "fleet-heartbeat"))
import fm_monitor as fm


class TestTrustCohort:
    """Trust cohort configuration."""

    def test_known_agents(self):
        assert fm.get_agent_trust("Forgemaster-AI") == 0.85
        assert fm.get_agent_trust("SuperInstance") == 0.90
        assert fm.get_agent_trust("JetsonClaw1") == 0.75

    def test_unknown_agent(self):
        assert fm.get_agent_trust("Stranger") == 0.5


class TestSynthesisDepth:
    """Trust-weighted synthesis depth selection."""

    def test_thorough(self):
        assert fm.synthesis_depth(0.90) == "thorough"
        assert fm.synthesis_depth(0.85) == "thorough"

    def test_standard(self):
        assert fm.synthesis_depth(0.80) == "standard"
        assert fm.synthesis_depth(0.70) == "standard"

    def test_minimal(self):
        assert fm.synthesis_depth(0.50) == "minimal"
        assert fm.synthesis_depth(0.30) == "minimal"


class TestCooperateInstinct:
    """COOPERATE instinct triggers."""

    def test_big_post_keywords(self):
        assert fm.check_cooperate_instinct("NEW REPO created", 0.90) is True
        assert fm.check_cooperate_instinct("ARCHITECTURE change", 0.85) is True
        assert fm.check_cooperate_instinct("MAJOR refactor", 0.80) is True

    def test_low_trust_blocks(self):
        assert fm.check_cooperate_instinct("NEW REPO", 0.3) is False

    def test_normal_post(self):
        assert fm.check_cooperate_instinct("just a normal update", 0.90) is False


class TestTrustUpdates:
    """Trust score updates on interaction."""

    def test_success_increases_trust(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"energy": 1.0, "threat": 0.0, "trust": {"User": 0.5}}, f)
            tmp = f.name
        with patch.object(fm, "INSTINCT_STATE", tmp):
            new_trust = fm.update_trust_on_interaction("User", success=True)
            assert new_trust > 0.5
            assert new_trust <= 1.0

    def test_failure_decreases_trust(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"energy": 1.0, "threat": 0.0, "trust": {"User": 0.5}}, f)
            tmp = f.name
        with patch.object(fm, "INSTINCT_STATE", tmp):
            new_trust = fm.update_trust_on_interaction("User", success=False)
            assert new_trust < 0.5
            assert new_trust >= 0.0

    def test_trust_capped_at_one(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"energy": 1.0, "threat": 0.0, "trust": {"User": 0.98}}, f)
            tmp = f.name
        with patch.object(fm, "INSTINCT_STATE", tmp):
            new_trust = fm.update_trust_on_interaction("User", success=True)
            assert new_trust <= 1.0

    def test_trust_floored_at_zero(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"energy": 1.0, "threat": 0.0, "trust": {"User": 0.05}}, f)
            tmp = f.name
        with patch.object(fm, "INSTINCT_STATE", tmp):
            new_trust = fm.update_trust_on_interaction("User", success=False)
            assert new_trust >= 0.0


class TestRouteScore:
    """Mycorrhizal route scoring."""

    def test_route_score_calculation(self):
        trust_log = {"interactions": 10, "successful_routes": {"primary": 8, "secondary": 2}}
        score_primary = fm.get_route_score("primary", trust_log)
        score_secondary = fm.get_route_score("secondary", trust_log)
        assert score_primary > score_secondary

    def test_zero_interactions(self):
        trust_log = {"interactions": 0, "successful_routes": {}}
        score = fm.get_route_score("unknown", trust_log)
        assert score == 0.0


class TestMycorrhizalFetch:
    """Mycorrhizal routing fallback."""

    def test_no_token_returns_none(self):
        # When there's no real HTTP server, all routes fail → returns None
        result = fm.mycorrhizal_fetch("http://localhost:99999/test", token="fake")
        assert result is None
