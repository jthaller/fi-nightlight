"""Single Cloud Function — runs every 5 min via Cloud Scheduler.

Exits early if not in the active window (before sunset or after cutoff).
"""

import logging

from fi_nightlight.check import check_and_toggle
from fi_nightlight.config import Config
from fi_nightlight.state import load_state, save_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fi_nightlight(request):
    """HTTP Cloud Function entry point."""
    config = Config.from_env()
    state = load_state()
    result = check_and_toggle(config, state)
    save_state(state)
    logger.info("Result: %s", result)
    return result
