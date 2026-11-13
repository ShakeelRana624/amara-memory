# 4. Modern Python Packaging with uv, src Layout, and Strict Typing

Date: 2026-11-13  
Status: Accepted

## Context

Professional Python libraries require reliable dependency resolution, reproducible developer environments, robust type contracts, and strict linting. Legacy setups relying on flat layouts, `setup.py`, or fragmented configurations often suffer from accidental import masking and typing inconsistencies.

## Decision

We adopt the following engineering baseline for AMARA:
1. **Python 3.12+**: Target modern Python to leverage enhanced typing syntax, performance improvements, and modern standard library capabilities.
2. **`uv` Package Manager**: Standardize on `uv` for virtual environment management, lockfile generation, and fast dependency resolution.
3. **`src` Layout**: Organize source code under `src/amara/` to prevent import collisions between local working directories and installed packages.
4. **Pydantic v2**: Standardize data validation, schema serialization, and configuration parsing on Pydantic v2.
5. **Strict `mypy` & Ruff**: Enforce strict static typing (`disallow_untyped_defs = true`) and unified linting/formatting via Ruff.
6. **UTC Timestamps**: Mandate timezone-aware UTC timestamps across all models and loggers to eliminate timezone ambiguity.

## Consequences

### Positive
- High developer velocity and instant linting/formatting cycles.
- Eliminates import path confusion during testing.
- Strong static type guarantees reduce runtime errors across public APIs.
- Predictable and uniform code style across the entire codebase.

### Negative / Considerations
- Requires developers to maintain Python 3.12+ installations.
- Strict typing requires writing complete type annotations for all functions and test fixtures.
