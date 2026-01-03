from .config import get_settings
from .database import get_supabase, get_supabase_agent


                  
__version__ = "1.0.0"
__author__ = "CaptureCloud Development Team"
__description__ = "AI-powered agent service for photography booking platform"


                            
__all__ = [
    "get_settings",
    "get_supabase", 
    "get_supabase_admin"
]