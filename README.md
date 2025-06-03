# SmashMate Backend

A FastAPI backend for Smash Mate with Supabase and PostGIS integration.

## Tech Stack

- Python 3.11+
- uv (Package Manager)
- FastAPI
- SQLAlchemy 2.0 (Async)
- Supabase
- PostGIS
- Alembic
- TrueSkill
- PyTest

## Setup

1. Install uv (Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Initialize the project and install dependencies:
```bash
# Initialize project
uv init

# Install dependencies
uv sync
```

3. Activate the virtual environment:
```bash
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

4. Set up local Supabase:
```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Start local Supabase
supabase start
```

5. Create a `.env` file in the root directory with the following variables:
```env
ENVIRONMENT=development
DEBUG=true
```

## Development

1. Make sure the virtual environment is activated:
```bash
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

2. Start the FastAPI development server:
```bash
uvicorn app.main:app --reload
```

3. Access the API documentation:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Package Management

- Add new dependencies:
```bash
uv add <package-name>
```

- Add development dependencies:
```bash
uv add --dev <package-name>
```

- Sync dependencies:
```bash
uv sync
```

- Update dependencies:
```bash
uv pip compile
```

## Testing

Make sure the virtual environment is activated, then run:
```bash
pytest
```

## Database Migrations

1. Create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

2. Apply migrations:
```bash
alembic upgrade head
```

## Project Structure

```
app/
├── api/          # API endpoints
├── core/         # Core functionality
├── models/       # SQLAlchemy models
├── schemas/      # Pydantic schemas
└── services/     # Business logic

tests/
├── api/          # API tests
├── integration/  # Integration tests
└── unit/         # Unit tests
``` 