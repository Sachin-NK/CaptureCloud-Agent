from typing import Optional
from supabase import create_client, Client
from app.config import get_settings


_supabase: Optional[Client] = None
_supabase_agent: Optional[Client] = None

def _ensure_clients():
    global _supabase, _supabase_agent
    if _supabase is not None and _supabase_agent is not None:
        return
    settings = get_settings()
    try:
        if _supabase is None:
            _supabase = create_client(settings.supabase_url, settings.supabase_key)
    except Exception as e:
        _supabase = None
    try:
        if _supabase_agent is None:
            _supabase_agent = create_client(settings.supabase_url, settings.supabase_service_key)
    except Exception as e:
        _supabase_agent = None

def get_supabase() -> Optional[Client]:
    _ensure_clients()
    return _supabase

def get_supabase_agent() -> Optional[Client]:
    _ensure_clients()
    return _supabase_agent

def set_user_context(db: Client, access_token: str, refresh_token: Optional[str] = None):
    if not db:
        return
    db.auth.set_session({
        "access_token": access_token,
        "refresh_token": refresh_token
    })

def clear_user_context(db: Client):
    if not db:
        return
    db.auth.sign_out()
