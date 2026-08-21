import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pytryfi import PyTryFi

from fi_nightlight.config import Config
from fi_nightlight.sunset import get_sunset_sunrise

logger = logging.getLogger(__name__)


def is_active_window(sunset: datetime, cutoff_hour: int, now: datetime) -> bool:
    """True if now is between sunset and cutoff_hour.

    Handles day rollover: cutoff_hour < 12 is treated as next-day
    (e.g. cutoff=1 means 1am the following day).
    """
    cutoff = now.replace(hour=cutoff_hour, minute=0, second=0, microsecond=0)
    if cutoff_hour < 12 and now.hour >= 12:
        cutoff += timedelta(days=1)
    return sunset <= now < cutoff


def get_pet(fi: PyTryFi, pet_name: str | None):
    """Get the pet by name, or the first pet if no name given."""
    if not fi.pets:
        raise RuntimeError("No pets found on this Fi account")
    if pet_name:
        for pet in fi.pets:
            if pet.name.lower() == pet_name.lower():
                return pet
        available = [p.name for p in fi.pets]
        raise RuntimeError(f"Pet '{pet_name}' not found. Available: {available}")
    return fi.pets[0]


def is_outside_safe_zone(pet) -> bool | None:
    """Check if the pet is outside their safe zone.

    Uses currPlaceName (which Fi sets to "Home" when in the safe zone)
    as the primary signal. Falls back to areaName if available.

    Returns True (outside), False (inside), or None (can't determine).
    """
    place = getattr(pet, "currPlaceName", None)
    area = getattr(pet, "areaName", None)
    logger.info("Pet '%s' place=%s, area=%s", pet.name, place, area)

    # currPlaceName is the most reliable indicator from the Fi API
    if place is not None:
        if place == "Home":
            return False  # inside safe zone
        return True  # outside safe zone

    # Fall back to areaName if currPlaceName is unavailable
    if area is not None:
        bases = getattr(pet, "bases", [])
        base_names = [b.name for b in bases if hasattr(b, "name")]
        if any(name == area for name in base_names):
            return False
        if base_names:
            return True

    logger.warning("Could not determine zone status (place=%s, area=%s)", place, area)
    return None


def connect_fi(config: Config) -> tuple[PyTryFi, object]:
    """Connect to Fi and return (fi_client, pet)."""
    fi = PyTryFi(config.fi_username, config.fi_password)
    pet = get_pet(fi, config.pet_name)
    return fi, pet


def check_and_toggle(config: Config, state: dict, now: datetime | None = None) -> dict:
    """Main check logic. Modifies state dict in place. Returns status dict."""
    tz = ZoneInfo(config.timezone)
    now = now or datetime.now(tz)

    sunset, _ = get_sunset_sunrise(
        config.latitude, config.longitude, config.timezone, now.date()
    )

    if not is_active_window(sunset, config.cutoff_hour, now):
        if state["led_on"]:
            logger.info("Outside active window, turning LED off")
            fi, pet = connect_fi(config)
            pet.turnOnOffLed(fi.session, False)
            state["led_on"] = False
        return {"action": "inactive", "led_on": False}

    # Throttle polling when dog is inside (LED off) — use slow interval
    if not state["led_on"] and state.get("last_checked"):
        last = datetime.fromisoformat(state["last_checked"])
        elapsed = (now - last).total_seconds() / 60
        if elapsed < config.slow_poll_interval_minutes:
            logger.info("Dog inside, %.0fm since last check (slow interval %dm) — skipping",
                        elapsed, config.slow_poll_interval_minutes)
            return {"action": "throttled", "led_on": False}

    # In active window — check zone
    fi, pet = connect_fi(config)
    pet.updatePetLocation(fi.session)
    outside = is_outside_safe_zone(pet)

    if outside is None:
        logger.warning("Zone status unknown, skipping toggle")
        state["last_checked"] = now.isoformat()
        return {"action": "unknown_zone", "led_on": state["led_on"]}

    if outside:
        color_index = state.get("color_index", 0) % len(config.led_colors)
        color = config.led_colors[color_index]
        if not state["led_on"]:
            logger.info("Dog OUTSIDE safe zone — turning LED ON (color %d)", color)
            pet.turnOnOffLed(fi.session, True)
        else:
            logger.info("Dog OUTSIDE safe zone — cycling to color %d", color)
        pet.setLedColorCode(fi.session, color)
        state["led_on"] = True
        state["color_index"] = (color_index + 1) % len(config.led_colors)
    elif not outside and state["led_on"]:
        logger.info("Dog INSIDE safe zone — turning LED OFF")
        pet.turnOnOffLed(fi.session, False)
        state["led_on"] = False
        state["color_index"] = 0
    else:
        logger.info("No change: inside, LED already off")

    state["last_checked"] = now.isoformat()
    return {"action": "checked", "outside": outside, "led_on": state["led_on"]}
