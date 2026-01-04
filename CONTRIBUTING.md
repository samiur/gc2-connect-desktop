# Contributing to GC2 Connect Desktop

Thank you for your interest in contributing to GC2 Connect Desktop! This document provides guidelines and instructions for development.

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for package management
- libusb for USB communication
- Git for version control

### Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/samiur/gc2-connect-desktop.git
   cd gc2-connect-desktop
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Run the app:
   ```bash
   uv run python -m gc2_connect.main
   ```

## Development Workflow

### Code Style

- Follow PEP 8 conventions
- Use type hints throughout
- Maximum line length: 100 characters
- Use Annotated[Type, Field(...)] for Pydantic fields

All Python files must start with a 2-line ABOUTME comment explaining the file's purpose:

```python
# ABOUTME: Brief description of what this module does.
# ABOUTME: Additional context about its role in the application.
```

### Running Tests

We practice Test-Driven Development (TDD). Write tests before implementation.

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=gc2_connect --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_models.py -v

# Run tests matching pattern
uv run pytest -k "test_physics" -v
```

### Type Checking

```bash
# Run mypy
uv run mypy src/

# Check specific module
uv run mypy src/gc2_connect/open_range/
```

### Linting and Formatting

```bash
# Check linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Check formatting
uv run ruff format --check .

# Auto-format
uv run ruff format .
```

### Running All CI Checks

Before submitting a PR, run all checks:

```bash
uv run pytest && uv run mypy src/ && uv run ruff check . && uv run ruff format --check .
```

Pre-commit hooks are configured to run these automatically:

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files
```

## Project Structure

```
src/gc2_connect/
├── main.py              # Entry point
├── models.py            # Shared data models
├── gc2/                 # GC2 USB communication
│   └── usb_reader.py
├── gspro/               # GSPro API client
│   └── client.py
├── open_range/          # Open Range feature
│   ├── models.py        # Trajectory models
│   ├── engine.py        # High-level engine
│   ├── physics/         # Physics simulation
│   └── visualization/   # 3D rendering
├── services/            # Shared services
│   ├── shot_router.py   # Mode routing
│   ├── history.py       # Shot history
│   └── export.py        # CSV export
├── ui/                  # NiceGUI interface
│   ├── app.py
│   └── components/
├── config/              # Settings management
│   └── settings.py
└── utils/               # Utility modules
    └── reconnect.py

tests/
├── unit/               # Unit tests
├── integration/        # Integration tests
├── e2e/                # End-to-end tests
├── simulators/         # Test infrastructure
│   ├── gc2/            # GC2 USB packet simulator
│   ├── gspro/          # Mock GSPro server
│   └── timing.py       # Time controller
└── conftest.py         # Shared fixtures
```

## Testing Without Hardware

The test infrastructure allows full testing without a physical GC2 device:

### GC2 USB Simulator

Generate realistic USB packets matching real GC2 behavior:

```python
from tests.simulators.gc2 import SimulatedPacketSource, create_two_phase_transmission_sequence
from tests.simulators.timing import TimeController, TimeMode

# Create a shot sequence
sequence = create_two_phase_transmission_sequence(shot_id=1, ball_speed=145.0)

# Use INSTANT mode for fast tests
time_controller = TimeController(mode=TimeMode.INSTANT)
source = SimulatedPacketSource(sequence, time_controller)
```

### Mock GSPro Server

Test GSPro integration without running the real server:

```python
from tests.simulators.gspro import MockGSProServer, MockGSProServerConfig, ResponseType

config = MockGSProServerConfig(
    response_delay_ms=100,
    response_type=ResponseType.SUCCESS
)

async with MockGSProServer(config) as server:
    # Connect to server.host:server.port
    # Send shots and verify with server.get_shots()
    pass
```

## Making Changes

### Branching Strategy

- `main` - Stable release branch
- Feature branches: `feat/feature-name`
- Bug fixes: `fix/bug-description`
- Documentation: `docs/description`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

Examples:
```
feat: add shot dispersion view to Open Range
fix: handle GC2 disconnect during shot transmission
docs: update README with Open Range instructions
test: add integration tests for mode switching
```

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes following the code style guidelines
3. Write tests for new functionality
4. Run all CI checks locally
5. Commit with descriptive messages
6. Push and create a pull request
7. Ensure CI passes
8. Request review

### PR Description Template

```markdown
## Summary
Brief description of changes

## Changes
- List of specific changes made

## Testing
- How the changes were tested
- Any new tests added

## Screenshots (if UI changes)
Before/after screenshots if applicable
```

## Physics Development

When working on the physics engine, reference:

- `docs/PHYSICS.md` - Physics model specification
- Nathan Model (Prof. Alan Nathan, UIUC)
- WSU Golf Ball Aerodynamics Research

Key files:
- `src/gc2_connect/open_range/physics/aerodynamics.py` - Drag and lift coefficients
- `src/gc2_connect/open_range/physics/trajectory.py` - RK4 integration
- `src/gc2_connect/open_range/physics/ground.py` - Bounce and roll

Validation tests are in `tests/unit/test_open_range/test_physics_validation.py`.

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Provide detailed reproduction steps for bugs
- Include system info (OS, Python version)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
