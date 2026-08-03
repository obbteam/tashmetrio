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

    MIN_PROGRESS_THRESHOLD: float = 1

    DEFAULT_DECEL_BUFFER_M: float = 5

    DEFAULT_LINE_SPEED: float = 10
    DEFAULT_LINE_ACCELERATION: float = 20

    DEFAULT_LINE_LENGTH_M: float = 2000


settings = Settings()
