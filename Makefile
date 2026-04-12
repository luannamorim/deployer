.PHONY: install dev lint test build up down logs clean

install:
	uv sync --extra dev

dev:
	uv run uvicorn deployer.main:app --reload --host 0.0.0.0 --port 8000

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run mypy src

format:
	uv run ruff check --fix src tests
	uv run ruff format src tests

test:
	uv run pytest tests/ --cov=src/deployer --cov-report=term-missing

test-unit:
	uv run pytest tests/unit/ -v

test-integration:
	uv run pytest tests/integration/ -v

build:
	docker build -t deployer:latest .

up:
	docker compose up --build

up-detach:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f app

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage .pytest_cache .mypy_cache .ruff_cache dist build
