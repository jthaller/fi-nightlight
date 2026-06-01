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

    Returns True (outside), False (inside), or None (can't determine).
    """
    area = getattr(pet, "areaName", None)
    logger.info("Pet '%s' area: %s", pet.name, area)

    if area is None:
        logger.warning("Could not determine pet area (areaName is None)")
        return None

    # Check against known bases/zones
    bases = getattr(pet, "bases", [])
    base_names = [b.name for b in bases if hasattr(b, "name")]
    logger.info("Known bases: %s", base_names)

    for base_name in base_names:
        if base_name == area:
            return False  # inside a known zone

    if not base_names:
        logger.warning(
            "No bases found for pet. Cannot determine zone status. "
            "Area reported as: '%s'", area
        )
        return None

    return True  # area doesn't match any known base


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

    # In active window — check zone
    fi, pet = connect_fi(config)
    pet.updatePetLocation(fi.session)
    outside = is_outside_safe_zone(pet)

    if outside is None:
        logger.warning("Zone status unknown, skipping toggle")
        state["last_checked"] = now.isoformat()
        return {"action": "unknown_zone", "led_on": state["led_on"]}

    if outside and not state["led_on"]:
        logger.info("Dog OUTSIDE safe zone — turning LED ON")
        pet.turnOnOffLed(fi.session, True)
        pet.setLedColorCode(fi.session, config.led_color)
        state["led_on"] = True
    elif not outside and state["led_on"]:
        logger.info("Dog INSIDE safe zone — turning LED OFF")
        pet.turnOnOffLed(fi.session, False)
        state["led_on"] = False
    else:
        status = "outside, LED already on" if outside else "inside, LED already off"
        logger.info("No change: %s", status)

    state["last_checked"] = now.isoformat()
    return {"action": "checked", "outside": outside, "led_on": state["led_on"]}
