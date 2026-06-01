from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import sun


def get_sunset_sunrise(
    latitude: float, longitude: float, timezone: str, for_date: date | None = None
) -> tuple[datetime, datetime]:
    """Calculate today's sunset and tomorrow's sunrise for the given location.

    Returns (sunset_tonight, sunrise_tomorrow) as timezone-aware datetimes.
    """
    tz = ZoneInfo(timezone)
    today = for_date or datetime.now(tz).date()

    location = LocationInfo(
        name="Home", region="", timezone=timezone,
        latitude=latitude, longitude=longitude,
    )

    today_sun = sun(location.observer, date=today, tzinfo=tz)
    tomorrow_sun = sun(location.observer, date=today + timedelta(days=1), tzinfo=tz)

    return today_sun["sunset"], tomorrow_sun["sunrise"]
