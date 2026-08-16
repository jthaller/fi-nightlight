import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_STATE = {"led_on": False, "last_checked": "", "color_index": 0}


def load_state() -> dict:
    if os.environ.get("GCP_PROJECT_ID"):
        return _load_firestore()
    return _load_json()


def save_state(state: dict) -> None:
    if os.environ.get("GCP_PROJECT_ID"):
        _save_firestore(state)
    else:
        _save_json(state)


def _load_json() -> dict:
    path = Path(os.environ.get("STATE_FILE", "state.json"))
    if not path.exists():
        return dict(DEFAULT_STATE)
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read state file, resetting: %s", e)
        return dict(DEFAULT_STATE)


def _save_json(state: dict) -> None:
    path = Path(os.environ.get("STATE_FILE", "state.json"))
    path.write_text(json.dumps(state, indent=2))


def _load_firestore() -> dict:
    from google.cloud import firestore

    project = os.environ["GCP_PROJECT_ID"]
    collection = os.environ.get("FIRESTORE_COLLECTION", "fi_nightlight")
    db = firestore.Client(project=project)
    doc = db.collection(collection).document("state").get()
    if not doc.exists:
        return dict(DEFAULT_STATE)
    return doc.to_dict()


def _save_firestore(state: dict) -> None:
    from google.cloud import firestore

    project = os.environ["GCP_PROJECT_ID"]
    collection = os.environ.get("FIRESTORE_COLLECTION", "fi_nightlight")
    db = firestore.Client(project=project)
    db.collection(collection).document("state").set(state)
