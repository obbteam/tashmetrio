from datetime import timedelta
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_PATH = Path(__file__).parent


class KafkaSettings(BaseModel):
    BOOTSTRAP_SERVERS: str | list[str]
    MAX_RETRIES: int = 3


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_PATH.parent / ".env",
        extra="ignore",
        env_nested_delimiter="__",
    )

    base_path: Path = BASE_PATH

    DATABASE_URL: str

    MIN_PROGRESS_THRESHOLD: float = 0.0
    
    MIN_TIME_AT_STATION_S: float = 20.0

    DEFAULT_DECEL_BUFFER: float = 0.2

    DEFAULT_LINE_SPEED: float = 10
    DEFAULT_LINE_ACCELERATION: float = 20

    DEFAULT_LINE_LENGTH_M: float = 2000

    DEFAULT_ETA_MINUTES: int = 1

    DEFAULT_TURNAROUND_BUFFER_MINUTES: int = 5

    SIMULATOR_SLEEP_TIME_S: float = 0.2
    GENERATOR_SLEEP_TIME_S: float = 60 * 60 * 6

    KAFKA: KafkaSettings


class BrokerTopic(StrEnum):
    TRAINS_POSITIONS = "trains.positions"
    NETWORK_ALERTS = "network.alerts"


settings = Settings()
