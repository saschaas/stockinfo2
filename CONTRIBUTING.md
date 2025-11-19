# Contributing to StockInfo

Thank you for your interest in contributing to StockInfo! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Git

### Quick Setup

```bash
# Clone the repository
git clone <repository-url>
cd StockInfo

# Install dependencies
make dev-install

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d postgres redis

# Initialize database
make db-init

# Install pre-commit hooks
pre-commit install
```

## Development Workflow

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or fixes

Example: `feature/add-portfolio-tracking`

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting, missing semicolons
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance

Examples:
```
feat(stocks): add RSI indicator calculation
fix(api): handle missing ticker gracefully
docs(readme): update installation instructions
```

### Code Style

#### Python

- Follow PEP 8
- Use type hints
- Maximum line length: 88 characters (Black default)
- Use `ruff` for linting and formatting

```bash
# Format code
make format-backend

# Check linting
make lint-backend
```

#### TypeScript/React

- Use functional components with hooks
- Use TypeScript strict mode
- Follow React best practices

```bash
# Format code
make format-frontend

# Check linting
make lint-frontend
```

### Testing

#### Backend Tests

```bash
# Run all backend tests
make test-backend

# Run with coverage
make test-cov

# Run specific test
pytest backend/tests/test_api.py -v
```

#### Frontend Tests

```bash
# Run frontend tests
make test-frontend
```

### Pre-commit Hooks

Pre-commit hooks run automatically on each commit:

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Commit** with clear messages
6. **Push** to your fork
7. **Open** a pull request

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated (if needed)
- [ ] Commits follow conventional format
- [ ] No sensitive data in commits
- [ ] PR description explains changes

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
How was this tested?

## Screenshots
If applicable, add screenshots
```

## Project Structure

```
StockInfo/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # REST endpoints
│   │   ├── core/        # Utilities
│   │   ├── db/          # Database models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # External services
│   │   └── tasks/       # Celery tasks
│   ├── migrations/      # Alembic migrations
│   └── tests/           # Backend tests
├── agents/              # AI agents
├── pipelines/           # Dagster pipelines
├── frontend/            # React frontend
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── services/
│       └── stores/
└── config/              # Configuration
```

## Adding New Features

### New API Endpoint

1. Add schema in `backend/app/schemas/`
2. Add route in `backend/app/api/routes/`
3. Add business logic in `backend/app/services/`
4. Add tests in `backend/tests/`
5. Update API documentation

### New React Component

1. Create component in `frontend/src/components/`
2. Add types in component file
3. Add tests
4. Export from index file

### New Data Source

1. Create client in `backend/app/services/`
2. Add rate limiting configuration
3. Add caching strategy
4. Create Dagster asset if scheduled
5. Add tests

### New AI Agent

1. Create agent in `agents/`
2. Define prompts
3. Add to supervisor workflow
4. Add tests
5. Document capabilities

## Database Migrations

```bash
# Create new migration
make db-migrate
# Enter migration message when prompted

# Apply migrations
make db-upgrade

# Rollback last migration
make db-downgrade
```

## Running Services

```bash
# Start all with Docker
make docker-up

# Or run individually:
make run-backend    # FastAPI
make run-frontend   # React
make run-celery     # Celery worker
make run-dagster    # Dagster
```

## Troubleshooting

### Common Issues

**Import errors**
```bash
pip install -e .
```

**Database connection**
```bash
docker-compose up -d postgres
```

**Redis connection**
```bash
docker-compose up -d redis
```

**Type errors**
```bash
make type-check
```

## Getting Help

- Check existing issues
- Read the documentation
- Open a new issue with:
  - Clear description
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
