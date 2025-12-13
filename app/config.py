from pydantic_settings import BaseSettings, SettingsConfigDict 
from functools import lru_cache 

class Settings(BaseSettings):
    
    supabase_url: str  
    supabase_key: str  
    supabase_service_key: str 
    
    openai_api_key: str 
    
    service_port: int = 8001 
    environment: str = "development" 
    
    redis_url: str = "redis://localhost:6379/0" 

    backend_url: str = "http://localhost:8080"
    
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file="app/.env",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache()  # Cache decorator 
def get_settings():
    return Settings()
