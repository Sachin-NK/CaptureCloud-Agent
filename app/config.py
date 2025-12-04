from pydantic_settings import BaseSettings 
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
    
    class Config:
       
        env_file = ".env" 
        case_sensitive = False 

@lru_cache()  # Cache decorator 
def get_settings():
    return Settings()
