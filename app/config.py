from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path

class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_service_key: str | None = None

    openai_api_key: str

    service_port: int = 8081
    environment: str = "development"

    redis_url: str = "redis://localhost:6379/0"
    backend_url: str = "http://localhost:8080"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).with_name(".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",                            
    )

    @field_validator("supabase_url", "supabase_key", "supabase_service_key", mode="before")
    def strip_vals(cls, v):
        return v.strip() if isinstance(v, str) else v

def get_settings() -> Settings:
    return Settings()
