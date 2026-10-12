# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email security concerns to the project maintainers directly.

## Security Practices

This project follows these security practices:

### Source Code
- No secrets, API keys, or credentials are committed to the repository
- Environment-based configuration for all sensitive values
- `.env` files are gitignored
- All GCP service account keys are excluded

### Data
- No proprietary or confidential enterprise data is included
- All datasets are synthetic or publicly available
- No internal schemas, logs, screenshots, or architecture documents from real organizations

### Application
- Input validation on all API endpoints
- File type and size validation on uploads
- Parameterized database queries (via SQLAlchemy ORM)
- Structured error responses that don't expose internal details
- CORS configured per environment

### Infrastructure
- Docker containers run as non-root where possible
- Dependency scanning via GitHub Actions
- Container scanning recommended for production deployments
- Terraform state files are gitignored

### Dependencies
- Regular dependency updates recommended
- `pip-audit` or equivalent scanning in CI pipeline
- Minimal dependency surface — no unnecessary packages

## Disclosure Policy

We follow a 90-day disclosure policy. After reporting, we will:

1. Acknowledge receipt within 48 hours
2. Provide an initial assessment within 7 days
3. Release a fix within 90 days (or sooner)
