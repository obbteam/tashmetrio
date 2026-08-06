from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_PATH = Path(__file__).parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_PATH.parent / ".env",
        extra="ignore",
    )

    base_path: Path = BASE_PATH

    DATABASE_URL: str

    MIN_PROGRESS_THRESHOLD: float = 0.0

    DEFAULT_DECEL_BUFFER: float = 0.2

    DEFAULT_LINE_SPEED: float = 10
    DEFAULT_LINE_ACCELERATION: float = 20

    DEFAULT_LINE_LENGTH_M: float = 2000
    
    DEFAULT_ETA_MINUTES: int = 30

    DEFAULT_TURNAROUND_BUFFER_MINUTES: int = 5
    
    SIMULATOR_SLEEP_TIME_S: float = .2
    GENERATOR_SLEEP_TIME_S: float = 60 * 60 * 6


settings = Settings()
