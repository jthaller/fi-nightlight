from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from fi_nightlight.check import is_active_window, check_and_toggle

TZ = ZoneInfo("America/New_York")


# --- is_active_window tests ---

def _sunset():
    """Standard summer sunset at 8:30pm."""
    return datetime(2026, 6, 15, 20, 30, tzinfo=TZ)


class TestIsActiveWindow:
    def test_after_sunset_before_cutoff(self):
        now = datetime(2026, 6, 15, 21, 0, tzinfo=TZ)  # 9pm
        assert is_active_window(_sunset(), cutoff_hour=1, now=now) is True

    def test_before_sunset(self):
        now = datetime(2026, 6, 15, 19, 0, tzinfo=TZ)  # 7pm
        assert is_active_window(_sunset(), cutoff_hour=1, now=now) is False

    def test_after_cutoff(self):
        now = datetime(2026, 6, 16, 2, 0, tzinfo=TZ)  # 2am next day
        assert is_active_window(_sunset(), cutoff_hour=1, now=now) is False

    def test_at_cutoff_exactly(self):
        now = datetime(2026, 6, 16, 1, 0, tzinfo=TZ)  # exactly 1am
        assert is_active_window(_sunset(), cutoff_hour=1, now=now) is False

    def test_just_before_cutoff(self):
        now = datetime(2026, 6, 16, 0, 59, tzinfo=TZ)  # 12:59am
        assert is_active_window(_sunset(), cutoff_hour=1, now=now) is True

    def test_cutoff_22_before(self):
        """cutoff=22 means stop at 10pm same day."""
        now = datetime(2026, 6, 15, 21, 30, tzinfo=TZ)  # 9:30pm
        assert is_active_window(_sunset(), cutoff_hour=22, now=now) is True

    def test_cutoff_22_after(self):
        now = datetime(2026, 6, 15, 22, 30, tzinfo=TZ)  # 10:30pm
        assert is_active_window(_sunset(), cutoff_hour=22, now=now) is False

    def test_cutoff_midnight(self):
        """cutoff=0 means midnight — should be active at 11:59pm."""
        now = datetime(2026, 6, 15, 23, 59, tzinfo=TZ)
        assert is_active_window(_sunset(), cutoff_hour=0, now=now) is True

    def test_cutoff_midnight_after(self):
        now = datetime(2026, 6, 16, 0, 1, tzinfo=TZ)
        assert is_active_window(_sunset(), cutoff_hour=0, now=now) is False

    def test_at_sunset_exactly(self):
        assert is_active_window(_sunset(), cutoff_hour=1, now=_sunset()) is True


# --- check_and_toggle tests ---

def _make_mock_fi(place_name="Some Street", base_names=None):
    """Create mock Fi client and pet.

    place_name maps to currPlaceName (Fi sets this to "Home" when in safe zone).
    """
    mock_pet = MagicMock()
    mock_pet.name = "Buddy"
    mock_pet.currPlaceName = place_name
    mock_pet.areaName = None  # typically None in real API responses
    mock_pet.bases = []
    if base_names:
        for name in base_names:
            base = MagicMock()
            base.name = name
            mock_pet.bases.append(base)

    mock_fi = MagicMock()
    mock_fi.pets = [mock_pet]
    mock_fi.session = MagicMock()
    return mock_fi, mock_pet


class TestCheckAndToggle:
    @patch("fi_nightlight.check.connect_fi")
    def test_turns_on_when_outside(self, mock_connect, config, state_off):
        fi, pet = _make_mock_fi("Main Street", ["Home"])
        mock_connect.return_value = (fi, pet)
        now = datetime(2026, 6, 15, 21, 0, tzinfo=TZ)

        result = check_and_toggle(config, state_off, now=now)

        assert result["led_on"] is True
        assert result["outside"] is True
        assert state_off["led_on"] is True
        pet.turnOnOffLed.assert_called_once_with(fi.session, True)
        pet.setLedColorCode.assert_called_once_with(fi.session, 2)  # first rainbow color (Red)

    @patch("fi_nightlight.check.connect_fi")
    def test_turns_off_when_inside(self, mock_connect, config, state_on):
        fi, pet = _make_mock_fi("Home", ["Home"])
        mock_connect.return_value = (fi, pet)
        now = datetime(2026, 6, 15, 21, 0, tzinfo=TZ)

        result = check_and_toggle(config, state_on, now=now)

        assert result["led_on"] is False
        assert result["outside"] is False
        assert state_on["led_on"] is False
        pet.turnOnOffLed.assert_called_once_with(fi.session, False)

    @patch("fi_nightlight.check.connect_fi")
    def test_cycles_color_when_already_on(self, mock_connect, config, state_on):
        fi, pet = _make_mock_fi("Main Street", ["Home"])
        mock_connect.return_value = (fi, pet)
        now = datetime(2026, 6, 15, 21, 0, tzinfo=TZ)

        result = check_and_toggle(config, state_on, now=now)

        assert result["led_on"] is True
        # Must toggle off then on to force collar to apply new color
        assert pet.turnOnOffLed.call_count == 2
        pet.turnOnOffLed.assert_any_call(fi.session, False)
        pet.turnOnOffLed.assert_any_call(fi.session, True)
        pet.setLedColorCode.assert_called_once_with(fi.session, 2)  # cycles to first color
        assert state_on["color_index"] == 1  # advanced to next

    @patch("fi_nightlight.check.connect_fi")
    def test_turns_off_outside_window(self, mock_connect, config, state_on):
        fi, pet = _make_mock_fi("Home", ["Home"])
        mock_connect.return_value = (fi, pet)
        now = datetime(2026, 6, 16, 2, 0, tzinfo=TZ)  # 2am, past cutoff

        result = check_and_toggle(config, state_on, now=now)

        assert result["action"] == "inactive"
        assert result["led_on"] is False
        assert state_on["led_on"] is False
        pet.turnOnOffLed.assert_called_once_with(fi.session, False)

    @patch("fi_nightlight.check.connect_fi")
    def test_inactive_no_connect_when_led_off(self, mock_connect, config, state_off):
        """Don't even connect to Fi if outside window and LED already off."""
        now = datetime(2026, 6, 15, 14, 0, tzinfo=TZ)  # 2pm

        result = check_and_toggle(config, state_off, now=now)

        assert result["action"] == "inactive"
        mock_connect.assert_not_called()

    @patch("fi_nightlight.check.connect_fi")
    def test_unknown_zone_skips_toggle(self, mock_connect, config, state_off):
        """When zone can't be determined, don't toggle."""
        fi, pet = _make_mock_fi(None, [])  # no place name, no bases
        pet.areaName = None
        mock_connect.return_value = (fi, pet)
        now = datetime(2026, 6, 15, 21, 0, tzinfo=TZ)

        result = check_and_toggle(config, state_off, now=now)

        assert result["action"] == "unknown_zone"
        pet.turnOnOffLed.assert_not_called()

    @patch("fi_nightlight.check.connect_fi")
    def test_multiple_trips(self, mock_connect, config):
        """Dog goes out, comes back, goes out again — LED toggles each time."""
        now = datetime(2026, 6, 15, 21, 0, tzinfo=TZ)
        state = {"led_on": False, "last_checked": "", "color_index": 0}

        # Trip 1: dog goes outside
        fi, pet = _make_mock_fi("Park Ave", ["Home"])
        mock_connect.return_value = (fi, pet)
        check_and_toggle(config, state, now=now)
        assert state["led_on"] is True

        # Dog returns
        fi, pet = _make_mock_fi("Home", ["Home"])
        mock_connect.return_value = (fi, pet)
        check_and_toggle(config, state, now=now)
        assert state["led_on"] is False

        # Trip 2: dog goes outside again (advance past slow poll interval)
        now2 = now + timedelta(minutes=6)
        fi, pet = _make_mock_fi("Broadway", ["Home"])
        mock_connect.return_value = (fi, pet)
        check_and_toggle(config, state, now=now2)
        assert state["led_on"] is True
