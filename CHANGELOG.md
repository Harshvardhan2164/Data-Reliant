# Changelog

All notable changes to DataReliant will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project scaffolding and repository structure
- FastAPI application skeleton with health check
- PostgreSQL database schema (15 core tables)
- SQLAlchemy ORM models with Alembic migrations
- Docker Compose for local development (PostgreSQL, API, frontend)
- Structured logging with structlog
- Domain exception hierarchy with machine-readable error codes
- Pydantic settings with environment variable support
- CLI entry point with Click
- Makefile with development, testing, and deployment targets
- Contributing guide, Code of Conduct, Security policy
