from functools import lru_cache
from app.services.database import DatabaseService
from app.core.config import settings

@lru_cache()
def get_database_service() -> DatabaseService:
    """
    Create and cache a DatabaseService instance.
    
    Using lru_cache ensures we get the same instance across requests
    while still allowing for easy testing and configuration flexibility.
    """
    return DatabaseService(
        url=settings.supabase_url,
        key=settings.supabase_key
    )

# Dependency function for FastAPI
def get_db() -> DatabaseService:
    """FastAPI dependency to inject DatabaseService."""
    return get_database_service() 