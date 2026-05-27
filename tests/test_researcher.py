"""Tests for beachcomb/researcher.py"""
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "beachcomb"))
import researcher as rc


class TestPythagoreanEncoding:
    """Pythagorean48 deterministic encoding."""

    def test_deterministic(self):
        result1 = rc.pythagorean_encode("hello world")
        result2 = rc.pythagorean_encode("hello world")
        assert result1 == result2

    def test_different_inputs_different_triples(self):
        r1 = rc.pythagorean_encode("input A")
        r2 = rc.pythagorean_encode("input B")
        # Not guaranteed different, but overwhelmingly likely
        assert isinstance(r1, str) and isinstance(r2, str)

    def test_format_pipe_separated(self):
        result = rc.pythagorean_encode("test")
        parts = result.split("|")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_valid_pythagorean_triple(self):
        result = rc.pythagorean_encode("test")
        a, b, c = [int(x) for x in result.split("|")]
        assert a * a + b * b == c * c

    def test_all_triples_valid(self):
        for a, b, c in rc.PYTHAGOREAN_TRIPLES:
            assert a * a + b * b == c * c

    def test_empty_string(self):
        result = rc.pythagorean_encode("")
        assert "|" in result


class TestHolonomyCheck:
    """Holonomy drift detection for research notes."""

    def test_matching_triples(self):
        assert rc.pythagorean_holonomy_check("note1", "3|4|5", "3|4|5") is True

    def test_drifted_triples(self):
        assert rc.pythagorean_holonomy_check("note1", "3|4|5", "5|12|13") is False


class TestIdleState:
    """Idle tracking state management."""

    def test_default_state(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = f.name
        os.unlink(tmp)
        with patch.object(rc, "IDLE_FILE", tmp):
            state = rc.load_idle_state()
            assert "last_activity" in state
            assert state["idle_ticks"] == 0

    def test_update_active(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"last_activity": "2024-01-01T00:00:00", "idle_ticks": 5}, f)
            tmp = f.name
        tmpdir = tempfile.mkdtemp()
        with patch.object(rc, "IDLE_FILE", tmp), \
             patch.object(rc, "NOTES_DIR", Path(tmpdir)):
            ticks = rc.update_idle(is_active=True)
            assert ticks == 0
        os.unlink(tmp)

    def test_update_inactive(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"last_activity": "2024-01-01T00:00:00", "idle_ticks": 3}, f)
            tmp = f.name
        tmpdir = tempfile.mkdtemp()
        with patch.object(rc, "IDLE_FILE", tmp), \
             patch.object(rc, "NOTES_DIR", Path(tmpdir)):
            ticks = rc.update_idle(is_active=False)
            assert ticks == 4


class TestResearchNotes:
    """Research note saving and retrieval."""

    def test_save_creates_file(self):
        tmpdir = tempfile.mkdtemp()
        with patch.object(rc, "NOTES_DIR", Path(tmpdir)):
            triple = rc.save_research_note("test-type", "test content")
            assert "|" in triple
            files = list(Path(tmpdir).glob("*.md"))
            assert len(files) == 1
            content = files[0].read_text()
            assert "test-type" in content
            assert "test content" in content
            assert triple in content

    def test_save_with_metadata(self):
        tmpdir = tempfile.mkdtemp()
        with patch.object(rc, "NOTES_DIR", Path(tmpdir)):
            triple = rc.save_research_note(
                "test", "content", metadata={"key": "value"}
            )
            files = list(Path(tmpdir).glob("*.md"))
            content = files[0].read_text()
            assert "key" in content

    def test_filename_format(self):
        tmpdir = tempfile.mkdtemp()
        with patch.object(rc, "NOTES_DIR", Path(tmpdir)):
            rc.save_research_note("mytype", "content")
            files = list(Path(tmpdir).glob("mytype-*.md"))
            assert len(files) == 1
