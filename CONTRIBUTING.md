# Contributing to DataReliant

Thank you for considering contributing to DataReliant! This document provides guidelines for contributing.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/datareliant/datareliant.git
cd datareliant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install development dependencies
pip install -e ".[dev]"

# Start infrastructure
docker compose up -d postgres

# Run migrations
alembic upgrade head

# Start the API server
make serve
```

## Code Quality

Before submitting a pull request, ensure:

```bash
make format      # Auto-format code
make lint        # Check linting rules
make typecheck   # Run type checker
make test        # Run all tests
```

## Commit Messages

Use conventional commits:

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `test:` — Test additions/changes
- `refactor:` — Code refactoring
- `chore:` — Build/tooling changes

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all checks pass
4. Update documentation if needed
5. Submit a PR with a clear description

## Architecture

- **Business logic** belongs in `datareliant/` — never in routes or components
- **Routes** are thin wrappers that call service functions
- **Tests** must cover each quality rule, detector, and engine independently
- **Configuration** is separate from source code

## Code of Conduct

Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.
