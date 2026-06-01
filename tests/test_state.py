import json
import os
from pathlib import Path

from fi_nightlight.state import load_state, save_state


def test_json_roundtrip(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setenv("STATE_FILE", str(state_file))
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    state = {"led_on": True, "last_checked": "2026-06-15T21:00:00"}
    save_state(state)

    loaded = load_state()
    assert loaded["led_on"] is True
    assert loaded["last_checked"] == "2026-06-15T21:00:00"


def test_missing_file_returns_default(tmp_path, monkeypatch):
    state_file = tmp_path / "nonexistent.json"
    monkeypatch.setenv("STATE_FILE", str(state_file))
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    state = load_state()
    assert state["led_on"] is False


def test_corrupt_file_returns_default(tmp_path, monkeypatch):
    state_file = tmp_path / "bad.json"
    state_file.write_text("not json{{{")
    monkeypatch.setenv("STATE_FILE", str(state_file))
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    state = load_state()
    assert state["led_on"] is False


def test_respects_state_file_env(tmp_path, monkeypatch):
    custom_path = tmp_path / "custom_state.json"
    monkeypatch.setenv("STATE_FILE", str(custom_path))
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    save_state({"led_on": True, "last_checked": ""})
    assert custom_path.exists()
    assert json.loads(custom_path.read_text())["led_on"] is True
