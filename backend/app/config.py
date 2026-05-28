from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./study_efficiency.db")
    app_name: str = "Study Efficiency API"


def get_settings() -> Settings:
    return Settings()

