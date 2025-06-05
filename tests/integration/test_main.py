import os
from fastapi.testclient import TestClient

# Set minimal environment variables required by settings before importing app
os.environ.setdefault("LOCAL_SUPABASE_URL", "http://localhost")
os.environ.setdefault("LOCAL_SUPABASE_KEY", "key")
os.environ.setdefault("LOCAL_SUPABASE_PASSWORD", "password")
os.environ.setdefault("LOCAL_SUPABASE_DB_NAME", "db")
os.environ.setdefault("LOCAL_SUPABASE_DB_USER", "user")
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service")
os.environ.setdefault("SUPABASE_PASSWORD", "password")

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
