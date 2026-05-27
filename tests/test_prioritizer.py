"""Tests for work-queue/prioritizer.py"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "work-queue"))
import prioritizer as pq


class TestTrustWeights:
    """Trust weight configuration and lookup."""

    def test_known_sources(self):
        assert pq.get_trust_weight("casey") == 1.0
        assert pq.get_trust_weight("fm") == 0.8
        assert pq.get_trust_weight("subagent") == 0.5

    def test_default_source(self):
        assert pq.get_trust_weight("unknown") == 0.3

    def test_all_weights_in_range(self):
        for source, weight in pq.TRUST_WEIGHTS.items():
            assert 0.0 <= weight <= 1.0


class TestPriorityBands:
    """Priority band classification from text."""

    def test_survive_keywords(self):
        for kw in ["HEALTH", "DEAD", "DOWN", "CRASH", "BROKEN", "EMERGENCY", "P0", "CRITICAL", "URGENT", "ALERT"]:
            assert pq.parse_priority_band(f"fix {kw} now") == pq.BAND_SURVIVE

    def test_flee_keywords(self):
        for kw in ["DEFER", "WAIT", "BLOCK", "THREAT", "AVOID", "POSTPONE"]:
            assert pq.parse_priority_band(f"should {kw} this") == pq.BAND_FLEE

    def test_curious_keywords(self):
        for kw in ["RESEARCH", "EXPLORE", "INNOVATION", "PAPER", "DISSERTATION", "IMPROVE", "CURIOUS", "IDLE"]:
            assert pq.parse_priority_band(f"some {kw} task") == pq.BAND_CURIOUS

    def test_guard_default(self):
        assert pq.parse_priority_band("regular task") == pq.BAND_GUARD

    def test_band_ordering(self):
        assert pq.BAND_SURVIVE < pq.BAND_FLEE < pq.BAND_GUARD < pq.BAND_CURIOUS


class TestSourceDetection:
    """Detect task source from text."""

    def test_casey_detection(self):
        assert pq.detect_source("Casey wants this") == "casey"
        assert pq.detect_source("DIGENNARO review") == "casey"

    def test_fm_detection(self):
        assert pq.detect_source("FM says hello") == "fm"
        assert pq.detect_source("Forgemaster update") == "fm"

    def test_subagent_detection(self):
        assert pq.detect_source("subagent task") == "subagent"
        assert pq.detect_source("agent scaffold") == "subagent"

    def test_default(self):
        assert pq.detect_source("random text") == "default"


class TestScoreTask:
    """Task scoring: band → trust → P-level."""

    def test_survive_scores_highest(self):
        survive = pq.score_task(0, "casey", "P0 CRITICAL fix")
        guard = pq.score_task(0, "casey", "normal work")
        assert survive < guard  # lower = higher priority

    def test_trust_affects_score(self):
        high = pq.score_task(0, "casey", "same task")
        low = pq.score_task(0, "default", "same task")
        assert high < low  # casey gets better (lower) score

    def test_p0_beats_p2(self):
        p0 = pq.score_task(0, "default", "P0 urgent item")
        p2 = pq.score_task(0, "default", "P2 minor item")
        assert p0 < p2


class TestInstinctState:
    """Instinct state persistence."""

    def test_load_default(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            bad_path = f.name
        os.unlink(bad_path)
        with patch.object(pq, "INSTINCT_STATE", bad_path):
            state = pq.load_instinct_state()
            assert state["energy"] == 1.0
            assert state["threat"] == 0.0

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write('{"energy": 0.5, "threat": 0.3}')
            tmp = f.name
        with patch.object(pq, "INSTINCT_STATE", tmp):
            state = pq.load_instinct_state()
            assert state["energy"] == 0.5
            pq.save_instinct_state({"energy": 0.9, "threat": 0.1})
            loaded = pq.load_instinct_state()
            assert loaded["energy"] == 0.9
        os.unlink(tmp)


class TestInstinctCheck:
    """Instinct stack evaluation."""

    def test_survive_low_energy(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"energy": 0.1, "threat": 0.0, "trust": {}}, f)
            tmp = f.name
        with patch.object(pq, "INSTINCT_STATE", tmp):
            assert pq.instinct_check() == "SURVIVE"
        os.unlink(tmp)

    def test_flee_high_threat(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"energy": 0.5, "threat": 0.8, "trust": {}}, f)
            tmp = f.name
        with patch.object(pq, "INSTINCT_STATE", tmp), \
             patch.object(pq, "TODO_PATH", Path("/nonexistent")):
            assert pq.instinct_check() == "FLEE"
        os.unlink(tmp)

    def test_guard_with_tasks(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"energy": 0.5, "threat": 0.0, "trust": {}}, f)
            tmp = f.name
        todo = tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False)
        todo.write("- [ ] normal task\n")
        todo.close()
        with patch.object(pq, "INSTINCT_STATE", tmp), \
             patch.object(pq, "TODO_PATH", Path(todo.name)):
            assert pq.instinct_check() == "GUARD"
        os.unlink(tmp)
        os.unlink(todo.name)

    def test_curious_when_idle(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"energy": 0.5, "threat": 0.0, "trust": {}}, f)
            tmp = f.name
        with patch.object(pq, "INSTINCT_STATE", tmp), \
             patch.object(pq, "TODO_PATH", Path("/nonexistent")):
            assert pq.instinct_check() == "CURIOUS"
        os.unlink(tmp)


class TestBlockedTasks:
    """Task blocking detection."""

    def test_blocked_keyword(self):
        assert pq.is_blocked("BLOCKED by dependency") is True

    def test_casey_needs(self):
        assert pq.is_blocked("Casey needs to approve") is True

    def test_fm_needs(self):
        assert pq.is_blocked("FM needs to respond") is True

    def test_unblocked(self):
        assert pq.is_blocked("just do this") is False


class TestExecuteTask:
    """Task routing based on instinct band."""

    def test_survive_route(self):
        assert pq.execute_task(pq.BAND_SURVIVE, "casey", "CRITICAL DOWN") == "SURVIVE"

    def test_flee_route(self):
        assert pq.execute_task(pq.BAND_FLEE, "default", "DEFER this") == "DEFERRED"

    def test_curious_research(self):
        assert pq.execute_task(pq.BAND_CURIOUS, "fm", "explore new idea") == "RESEARCH"

    def test_curious_dissertation(self):
        assert pq.execute_task(pq.BAND_CURIOUS, "fm", "write dissertation chapter") == "DISSERTATION"

    def test_guard_dissertation(self):
        assert pq.execute_task(pq.BAND_GUARD, "casey", "finish dissertation") == "DISSERTATION"

    def test_guard_agent(self):
        assert pq.execute_task(pq.BAND_GUARD, "fm", "agent scaffold task") == "AGENT"

    def test_guard_infra(self):
        assert pq.execute_task(pq.BAND_GUARD, "fm", "plato infrastructure") == "INFRA"

    def test_guard_fm(self):
        assert pq.execute_task(pq.BAND_GUARD, "fm", "fm discussion reply") == "FM"

    def test_guard_unknown(self):
        assert pq.execute_task(pq.BAND_GUARD, "default", "random work") == "UNKNOWN"
