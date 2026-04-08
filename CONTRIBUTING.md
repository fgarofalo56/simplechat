# Contributing to SimpleChat

Thank you for your interest in contributing to SimpleChat! This guide covers local setup, coding standards, and how to submit changes.

## Quick Start

```bash
# 1. Clone and navigate
git clone https://github.com/microsoft/simplechat.git
cd simplechat

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
make install
# Or manually:
cd application/single_app
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Set up environment
cp application/single_app/.env.example application/single_app/.env
# Edit .env with your Azure service credentials

# 5. Run the development server
make dev
# Or: cd application/single_app && flask run --debug

# 6. Run tests
make test
```

## Project Structure

```
simplechat/
├── application/single_app/     # Main application
│   ├── app.py                  # Flask entry point
│   ├── config*.py              # Configuration modules
│   ├── functions_*.py          # Business logic
│   ├── route_*.py              # Route handlers
│   ├── services/               # Service layer (new)
│   ├── utils/                  # Utility modules (new)
│   ├── static/                 # Frontend assets
│   │   ├── css/                # Stylesheets
│   │   └── js/                 # JavaScript modules
│   ├── templates/              # Jinja2 HTML templates
│   ├── tests/                  # Test suite
│   │   ├── unit/               # Unit tests
│   │   └── integration/        # Integration tests
│   └── requirements.txt        # Python dependencies
├── docs/                       # Documentation
├── functional_tests/           # Legacy functional tests
├── Makefile                    # Developer workflow targets
└── .github/workflows/          # CI/CD pipelines
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-description
```

### 2. Make Changes

Follow the coding standards below. Key rules:

- **Python**: Start files with `# filename.py`, use 4-space indentation
- **JavaScript**: Start files with `// filename.js`, use 4-space indentation, camelCase
- **Templates**: All `<script>` tags must include `nonce="{{ csp_nonce }}"`

### 3. Run Tests

```bash
make test          # Full test suite with coverage
make test-unit     # Unit tests only (fast)
make lint          # Check linting
make format-check  # Check formatting
```

### 4. Submit a PR

- Write a clear PR description explaining what changed and why
- Reference any related issues
- Ensure all CI checks pass

## Coding Standards

### Python

- Start every file with `# filename.py`
- Use `log_event()` from `functions_appinsights.py` for logging (not `print()`)
- Use parameterized queries for all Cosmos DB operations (never f-string interpolation)
- Every route must include `@swagger_route(security=get_auth_security())`
- Never send raw settings to frontend — use `sanitize_settings_for_user()`

### JavaScript

- Start every file with `// filename.js`
- Use `escapeHtml()` from `dom-helpers.js` for untrusted content
- Use Bootstrap's `d-none` class instead of `display:none`
- Use Bootstrap alert classes, not `alert()` calls

### Security

- Never commit API keys, secrets, or `.env` files
- All `<script>` tags must include `nonce="{{ csp_nonce }}"`
- Use `sanitize_filename()` from `utils/sanitize.py` for user-provided filenames
- File upload endpoints must validate file extensions against `ALLOWED_EXTENSIONS`

### Testing

- Place unit tests in `tests/unit/test_*.py`
- Place integration tests in `tests/integration/test_*.py`
- Follow AAA pattern: Arrange, Act, Assert
- Target 80%+ coverage for new code

## Adding a New Route

1. Create or modify a `route_*.py` file
2. Add the swagger decorator:
   ```python
   @app.route("/api/your-endpoint", methods=["GET"])
   @swagger_route(security=get_auth_security())
   @login_required
   @user_required
   def your_endpoint():
       ...
   ```
3. Register the route in `app.py` if using the `register_route_*()` pattern
4. Add tests in `tests/`

## Available Make Targets

Run `make help` to see all available targets:

| Target | Description |
|--------|-------------|
| `make install` | Install all dependencies |
| `make dev` | Run Flask dev server |
| `make test` | Run tests with coverage |
| `make test-unit` | Run unit tests only |
| `make lint` | Run linter |
| `make format` | Format code |
| `make security` | Run dependency security scan |
| `make docker-build` | Build Docker image |
| `make clean` | Remove build artifacts |

## Questions?

Open an issue on GitHub or reach out to the maintainers.
