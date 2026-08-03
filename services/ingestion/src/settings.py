from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_PATH = Path(__file__).parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_PATH.parent / ".env",
        extra='ignore',
    )

    base_path: Path = BASE_PATH

    DATABASE_URL: str


settings = Settings()
