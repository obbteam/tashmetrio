from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_PATH = Path(__file__).parent


class BrokerTopic(StrEnum):
    TRAINS_POSITIONS = "trains.positions"
    NETWORK_ALERTS = "network.alerts"


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
    REDIS_URL: str

    KAFKA: KafkaSettings


settings = Settings()
