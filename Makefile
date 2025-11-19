.PHONY: help install dev-install test lint format clean docker-up docker-down docker-logs db-init db-migrate db-upgrade run-backend run-frontend run-celery run-dagster

# Default target
help:
	@echo "StockInfo - AI-Powered Stock Research Tool"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  install         Install production dependencies"
	@echo "  dev-install     Install development dependencies"
	@echo "  setup           Complete development setup"
	@echo ""
	@echo "Development:"
	@echo "  run-backend     Start FastAPI development server"
	@echo "  run-frontend    Start React development server"
	@echo "  run-celery      Start Celery worker"
	@echo "  run-dagster     Start Dagster webserver"
	@echo ""
	@echo "Testing:"
	@echo "  test            Run all tests"
	@echo "  test-backend    Run backend tests only"
	@echo "  test-frontend   Run frontend tests only"
	@echo "  test-cov        Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint            Run all linters"
	@echo "  format          Format all code"
	@echo "  type-check      Run type checking"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up       Start all services"
	@echo "  docker-down     Stop all services"
	@echo "  docker-logs     View service logs"
	@echo "  docker-build    Build Docker images"
	@echo ""
	@echo "Database:"
	@echo "  db-init         Initialize database with seed data"
	@echo "  db-migrate      Create new migration"
	@echo "  db-upgrade      Apply migrations"
	@echo "  db-downgrade    Rollback last migration"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean           Remove build artifacts"
	@echo "  clean-docker    Remove Docker volumes"

# Setup targets
install:
	pip install -e .

dev-install:
	pip install -e ".[dev,dagster]"
	cd frontend && npm install

setup: dev-install
	cp -n .env.example .env || true
	@echo "Setup complete! Edit .env with your API keys."

# Development servers
run-backend:
	uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	cd frontend && npm run dev

run-celery:
	celery -A backend.app.celery_app worker --loglevel=info

run-celery-beat:
	celery -A backend.app.celery_app beat --loglevel=info

run-dagster:
	dagster dev -m pipelines.definitions

# Testing
test: test-backend test-frontend

test-backend:
	pytest backend/tests -v

test-frontend:
	cd frontend && npm test

test-cov:
	pytest backend/tests -v --cov=backend --cov-report=html --cov-report=term

# Code quality
lint: lint-backend lint-frontend

lint-backend:
	ruff check backend agents pipelines
	mypy backend agents pipelines

lint-frontend:
	cd frontend && npm run lint

format: format-backend format-frontend

format-backend:
	ruff format backend agents pipelines
	ruff check --fix backend agents pipelines

format-frontend:
	cd frontend && npm run format

type-check:
	mypy backend agents pipelines

# Docker targets
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build

docker-init: docker-up
	docker-compose --profile init up db-init
	docker exec stockinfo-ollama ollama pull llama3.2

# Database targets
db-init:
	python backend/scripts/init_db.py

db-migrate:
	@read -p "Migration message: " msg; \
	cd backend && alembic revision --autogenerate -m "$$msg"

db-upgrade:
	cd backend && alembic upgrade head

db-downgrade:
	cd backend && alembic downgrade -1

db-reset:
	cd backend && alembic downgrade base && alembic upgrade head

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf htmlcov 2>/dev/null || true

clean-docker:
	docker-compose down -v
	docker system prune -f
