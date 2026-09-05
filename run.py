"""Local/Docker entry point — runs the check loop using APScheduler."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

from fi_nightlight.check import check_and_toggle
from fi_nightlight.config import Config
from fi_nightlight.state import load_state, save_state
from fi_nightlight.sunset import get_sunset_sunrise

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fi-nightlight")


def main():
    load_dotenv()
    config = Config.from_env()
    tz = ZoneInfo(config.timezone)

    sunset, sunrise = get_sunset_sunrise(config.latitude, config.longitude, config.timezone)
    logger.info("Sunset tonight: %s", sunset.strftime("%I:%M %p"))
    logger.info("Sunrise tomorrow: %s", sunrise.strftime("%I:%M %p"))
    logger.info("Checking every %d min (outside) / %d min (inside), cutoff at %d:00",
                config.poll_interval_minutes, config.slow_poll_interval_minutes, config.cutoff_hour)
    logger.info("LED color: %d", config.led_color)

    def do_check():
        state = load_state()
        result = check_and_toggle(config, state)
        save_state(state)
        logger.info("Result: %s", result)

    scheduler = BlockingScheduler()
    scheduler.add_job(
        do_check,
        IntervalTrigger(minutes=config.poll_interval_minutes, timezone=tz),
        id="zone-check",
        next_run_time=datetime.now(tz),  # run immediately on start
    )

    logger.info("Fi Nightlight started. Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down.")


if __name__ == "__main__":
    main()
