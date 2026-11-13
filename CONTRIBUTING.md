# Contributing to AMARA

Thank you for your interest in contributing to AMARA (Adaptive Memory Architecture for Reasoning and AI).

AMARA is designed to be a high-assurance, model-agnostic cognitive memory framework. To maintain code quality, security, and architectural coherence, all contributions are expected to adhere to the standards outlined below.

---

## Development Principles

1. **Cognitive Memory Scope**: AMARA focuses strictly on cognitive memory for reasoning agents (e.g., episodic events, working memory buffers, semantic associations, procedural sequences). Do not submit PRs for GPU CUDA kernels, low-level training memory optimizations, or parametric model weights.
2. **Zero Core Vendor Lock-In**: Core AMARA modules must never depend directly on proprietary LLM client libraries or specific cloud providers. Interfaces and protocols must remain abstract and model-agnostic.
3. **No Unnecessary Dependencies**: Every external dependency added to `pyproject.toml` incurs a maintenance, security, and compatibility cost. Dependencies must be justified and approved via an Architecture Decision Record (ADR) if structural.
4. **Strict Typing**: All functions, methods, and classes must provide explicit, complete type annotations. Untyped code or reliance on unchecked `Any` is not permitted in core modules.
5. **UTC-Aware Datetimes**: All timestamps must be explicitly timezone-aware and set to UTC (`datetime.datetime.now(datetime.timezone.utc)` or `datetime.timezone.utc`). Naive datetimes are strictly forbidden.

---

## Local Development Setup

We use `uv` as our primary environment and dependency manager.

1. **Prerequisites**: Ensure Python 3.12+ and `uv` are installed.
2. **Clone & Environment**:
   ```bash
   git clone https://github.com/amara-ai/amara.git
   cd amara
   uv venv
   ```
3. **Activate Environment**:
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
   - Linux/macOS: `source .venv/bin/activate`
4. **Install Dependencies in Editable Mode**:
   ```bash
   uv pip install -e ".[dev]"
   ```

---

## Quality Gates and Pre-Commit Checks

Before opening a pull request, verify that all quality gates pass locally:

```bash
# 1. Run linter checks
ruff check .

# 2. Run code formatter checks
ruff format --check .

# 3. Run static type analysis
mypy src tests

# 4. Run test suite
pytest
```

---

## Pull Request Guidelines

- **Focus**: Keep PRs focused on a single change, fix, or well-scoped feature.
- **Tests**: Every new feature or bug fix must include corresponding automated unit/integration tests in `tests/`.
- **Documentation**: Update documentation in `docs/` and docstrings where appropriate. If introducing a major architectural pattern, draft an ADR in `docs/decisions/`.
- **No Secrets**: Never commit tokens, credentials, or private configuration. Use `.env.example` as a template for environment variables.

