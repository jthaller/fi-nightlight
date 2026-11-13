import pytest

from fi_nightlight.config import Config


@pytest.fixture
def config():
    return Config(
        fi_username="test@test.com",
        fi_password="password",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
        pet_name=None,
        cutoff_hour=1,
        poll_interval_minutes=2,
        slow_poll_interval_minutes=5,
        led_color=5,
        state_file="test_state.json",
        gcp_project_id=None,
        firestore_collection="test",
    )


@pytest.fixture
def state_off():
    return {"led_on": False, "last_checked": ""}


@pytest.fixture
def state_on():
    return {"led_on": True, "last_checked": ""}
