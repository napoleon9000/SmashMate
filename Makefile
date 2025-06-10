.PHONY: help install test lint format clean db-start db-stop db-reset db-migrate test-file

# Variables
PYTHON := python3
UV := uv
SUPABASE := supabase

help: ## Display this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk -F ':|##' '/^[^\t].+?:.*?##/ { printf "  %-20s %s\n", $$1, $$NF }' $(MAKEFILE_LIST)

install: ## Install dependencies using uv
	$(UV) pip install -e .

test: ## Run tests with pytest
	$(UV) run pytest

test-file: ## Run a specific test file or function (usage: make test-file TEST=tests/test_supabase_crud.py::test_create_profile)
	$(UV) run pytest $(TEST)

test-cov: ## Run tests with coverage report
	$(UV) run pytest --cov=app --cov-report=term-missing

lint: ## Run linting checks
	$(UV) run ruff check .

format: ## Format code using ruff
	$(UV) run ruff format .

clean: ## Clean up Python cache files
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".ruff_cache" -exec rm -r {} +

# Database commands
db-start: ## Start local Supabase instance
	$(SUPABASE) start

db-stop: ## Stop local Supabase instance
	$(SUPABASE) stop

db-reset: ## Reset local database and apply migrations
	$(SUPABASE) db reset

db-migrate: ## Create a new migration
	@read -p "Enter migration name: " name; \
	$(SUPABASE) migration new $$name

# Development server
dev: ## Start development server
	$(UV) run uvicorn app.main:app --reload

run-streamlit: ## Check and start Supabase if needed, then run Streamlit app
	@echo "Checking Supabase status..."
	@if ! $(SUPABASE) status >/dev/null 2>&1; then \
		echo "Supabase is not running. Starting..."; \
		$(SUPABASE) start; \
	else \
		echo "Supabase is already running."; \
	fi
	@echo "Starting Streamlit app..."
	$(UV) run streamlit run app/streamlit/streamlit_app.py

# Database URL commands
db-url: ## Show database connection URLs
	@echo "Database URL: postgresql://postgres:postgres@localhost:54322/postgres"
	@echo "API URL: http://localhost:54321"
	@echo "Studio URL: http://localhost:54323"

# Initialize project
init: ## Initialize the project (first time setup)
	@echo "Initializing project..."
	@if [ ! -d "supabase" ]; then \
		$(SUPABASE) init; \
	fi
	@echo "Installing dependencies..."
	$(UV) pip install -e .
	@echo "Starting Supabase..."
	$(SUPABASE) start
	@echo "Applying migrations..."
	$(SUPABASE) db reset
	@echo "Project initialized successfully!"
	@echo "Run 'make help' to see available commands" 
