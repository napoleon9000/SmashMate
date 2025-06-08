"""
Dependency injection for FastAPI endpoints.
"""
import os
from app.services.database import DatabaseService

def get_database_service() -> DatabaseService:
    """Get database service instance with proper configuration."""
    # Use test environment variables if available (for testing)
    # Otherwise fall back to regular environment variables
    url = (
        os.getenv("LOCAL_SUPABASE_URL") or  # Test environment
        os.getenv("SUPABASE_URL")           # Production environment
    )
    key = (
        os.getenv("LOCAL_SUPABASE_KEY") or  # Test environment
        os.getenv("SUPABASE_ANON_KEY") or   # Production environment
        os.getenv("SUPABASE_KEY")           # Fallback
    )
    
    return DatabaseService(url, key) 