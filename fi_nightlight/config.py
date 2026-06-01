import os
from dataclasses import dataclass


@dataclass
class Config:
    fi_username: str
    fi_password: str
    latitude: float
    longitude: float
    timezone: str
    pet_name: str | None
    cutoff_hour: int
    poll_interval_minutes: int
    led_color: int
    state_file: str
    gcp_project_id: str | None
    firestore_collection: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            fi_username=os.environ["FI_USERNAME"],
            fi_password=os.environ["FI_PASSWORD"],
            latitude=float(os.environ["LATITUDE"]),
            longitude=float(os.environ["LONGITUDE"]),
            timezone=os.environ.get("TIMEZONE", "America/New_York"),
            pet_name=os.environ.get("PET_NAME") or None,
            cutoff_hour=int(os.environ.get("CUTOFF_HOUR", "1")),
            poll_interval_minutes=int(os.environ.get("POLL_INTERVAL_MINUTES", "5")),
            led_color=int(os.environ.get("LED_COLOR", "4")),
            state_file=os.environ.get("STATE_FILE", "state.json"),
            gcp_project_id=os.environ.get("GCP_PROJECT_ID") or None,
            firestore_collection=os.environ.get("FIRESTORE_COLLECTION", "fi_nightlight"),
        )
