from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, field_validator, ConfigDict, ValidationInfo
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "SmashMate"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Supabase Local
    LOCAL_SUPABASE_URL: str
    LOCAL_SUPABASE_KEY: str
    LOCAL_SUPABASE_PASSWORD: str
    LOCAL_SUPABASE_DB_NAME: str
    LOCAL_SUPABASE_DB_USER: str
    
    # Supabase Remote
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_PASSWORD: str

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://localhost:8080"]
    
    # Logging
    LOG_LEVEL: str = "INFO"

    # Generated URL
    LOCAL_DATABASE_URL: Optional[PostgresDsn] = None
    REMOTE_DATABASE_URL: Optional[PostgresDsn] = None

    @field_validator("LOCAL_DATABASE_URL", mode="before")
    @classmethod
    def assemble_local_db_url(cls, v: Optional[str], info: ValidationInfo):
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=info.data.get("SUPABASE_DB_USER"),
            password=info.data.get("SUPABASE_PASSWORD"),
            host="localhost",
            port=54322,
            path=f"/{info.data.get('SUPABASE_DB_NAME')}"
        )

    @field_validator("REMOTE_DATABASE_URL", mode="before")
    @classmethod
    def assemble_remote_db_url(cls, v: Optional[str], info: ValidationInfo):
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=info.data.get("SUPABASE_DB_USER"),
            password=info.data.get("SUPABASE_PASSWORD"),
            host="db.pjkmzaqkhqsmthhqabwr.supabase.co",
            port=5432,
            path="/postgres"
        )
    
    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env"
    )

settings = Settings() 
