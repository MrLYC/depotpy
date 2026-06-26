# Contributing

## Development Setup

```bash
# Clone the repository
git clone https://github.com/MrLYC/pydepot.git
cd pydepot

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Verify
pydepot --version
pytest tests/ -v
```

## Project Structure

```
pydepot/
├── src/pydepot/         # Source code (src layout)
│   ├── cli.py           # CLI entry point
│   ├── commands/        # Subcommand handlers
│   ├── detector.py      # Dependency manager detection
│   ├── resolver.py      # Package download
│   ├── manifest.py      # Manifest I/O
│   ├── packer.py        # Bundle creation
│   ├── installer.py     # Bundle installation
│   ├── models.py        # Data models
│   └── platforms.py     # Platform definitions
├── tests/               # Test suite
├── docs/                # Documentation
│   ├── en/              # English
│   └── zh/              # Chinese
├── pyproject.toml       # Project metadata and build config
└── README.md            # Project overview
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=pydepot --cov-report=term-missing

# Run a specific test file
pytest tests/test_detector.py -v

# Run a specific test
pytest tests/test_detector.py::TestDetectManager::test_uv_by_lockfile -v
```

## Code Style

- Python 3.11+ features are welcome (type hints, `match`, `tomllib`, etc.)
- Use `from __future__ import annotations` for postponed evaluation
- Prefer standard library over external dependencies
- Use `dataclasses` for data models
- External tool invocations go through `subprocess.run`

## Adding a New Dependency Manager

1. Add the manager to `DependencyManager` enum in `models.py`
2. Add detection logic in `detector.py`:
   - Check for lock file or tool section
   - Verify the tool is installed via `shutil.which`
3. Add download function in `resolver.py` if the tool has its own download command
4. Update `download_packages()` to route to the new function
5. Add tests for detection and download
6. Update documentation

## Adding a New Platform

1. Add the `PlatformTag` constant in `platforms.py`
2. Add it to the appropriate preset(s) in `PLATFORM_PRESETS`
3. Add tests
4. Update documentation

## Writing Tests

- Use `tmp_path` (pytest fixture) for file system tests
- Mock `subprocess.run` for external tool calls
- Mock `shutil.which` for tool detection tests
- Each module has its own test file (`test_{module}.py`)
- Group related tests in classes

## Commit Messages

Use clear, descriptive commit messages:

```
Add support for conda dependency manager

Detect conda environments via environment.yml and use conda to resolve
dependencies. Falls back to pip when conda is not available.
```

## Pull Requests

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation if the user-facing interface changes
- Ensure all tests pass and coverage doesn't decrease
