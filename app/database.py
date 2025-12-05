from typing import Optional
from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

# Regular Supabase client - uses the public anon key
supabase:Client = create_client(settings.supabase_url, settings.supabase_key)

# Agent Supabase client 
supabase_agent: Client = create_client(settings.supabase_url, settings.supabase_service_key)

def get_supabase() -> Client:
    return supabse

def get_supabase_agent() -> Client:
    return supabase_agent

def set_user_context(db: Client, access_token: str, refresh_token: Optional[str] = None):
    
    db.auth.set_session({
        "access_token": access_token,
        "refresh_token": refresh_token
    })

def clear_user_context(db: Client):
    db.auth.sign_out()
