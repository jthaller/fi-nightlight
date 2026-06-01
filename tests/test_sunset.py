from datetime import date

from fi_nightlight.sunset import get_sunset_sunrise


def test_summer_sunset_after_7pm():
    sunset, _ = get_sunset_sunrise(40.7128, -74.0060, "America/New_York", date(2026, 6, 21))
    assert sunset.hour >= 19


def test_winter_sunset_before_5pm():
    sunset, _ = get_sunset_sunrise(40.7128, -74.0060, "America/New_York", date(2026, 12, 21))
    assert sunset.hour <= 17


def test_sunrise_after_sunset():
    sunset, sunrise = get_sunset_sunrise(40.7128, -74.0060, "America/New_York", date(2026, 6, 21))
    assert sunrise > sunset


def test_dst_spring_forward():
    """March 8 2026 — DST transition shouldn't crash."""
    sunset, sunrise = get_sunset_sunrise(40.7128, -74.0060, "America/New_York", date(2026, 3, 8))
    assert sunset is not None
    assert sunrise is not None


def test_dst_fall_back():
    """Nov 1 2026 — DST transition shouldn't crash."""
    sunset, sunrise = get_sunset_sunrise(40.7128, -74.0060, "America/New_York", date(2026, 11, 1))
    assert sunset is not None
    assert sunrise is not None
