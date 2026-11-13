# AMARA: Adaptive Memory Architecture for Reasoning and AI

AMARA is an open-source, model-agnostic cognitive memory framework engineered to empower artificial intelligence systems and autonomous agents with structured, persistent, and adaptive cognitive context.

> **Project Phase**: Phase 10 — Quality Assurance, Security and Research Evaluation  
> **Status**: Comprehensive security audit, penetration testing, concurrency stress testing, empirical research evaluation (LongMemEval, LoCoMo, ablations), and release gate documentation (`SECURITY_AUDIT.md`, `TEST_REPORT.md`, `BENCHMARK_REPORT.md`, `KNOWN_LIMITATIONS.md`) fully completed and verified with 233 passing tests.

---

## Overview

Modern AI agents and reasoning workflows face a fundamental bottleneck: models are stateless, context windows are volatile and finite, and naive vector-store retrieval often lacks temporal awareness, cognitive hierarchy, and relational coherence.

AMARA addresses this challenge through a dedicated cognitive memory architecture:

- **Model-Agnostic Core**: Zero hard dependencies on external LLM SDKs or proprietary vendor APIs. Works seamlessly with any reasoning engine, model provider, or custom local architecture.
- **Cognitive Memory Focus**: Dedicated to cognitive structures (episodic, working, semantic, and procedural memory) rather than GPU hardware caching, model training memory, or parametric weight adaptation.
- **Strict Typing & Modern Tooling**: Built for Python 3.12+ with full typing discipline (strict `mypy`), data validation via Pydantic v2, and linting/formatting with Ruff.
- **Pluggable & Extensible**: Modular storage and indexing protocols allowing plug-and-play adoption across local and distributed storage topologies.
- **AI Framework Integrations**: Decoupled adapters and wrappers for LangGraph, Hugging Face Transformers, FastAPI external memory service, and generic Python agent loops with external prompt context augmentation and strict citation traceability.

---

## Repository Structure

```text
AMARA/
├── .github/
│   └── workflows/          # Continuous Integration and automation pipelines
├── benchmarks/             # Performance, retrieval latency, and resource benchmarks
├── docs/                   # Architectural blueprints and decision records
│   ├── architecture/       # Technical architecture documentation
│   └── decisions/          # Architecture Decision Records (ADRs)
├── examples/               # Runnable integration and usage examples
├── experiments/            # Exploratory research and algorithmic prototypes
├── src/
│   └── amara/              # Core AMARA framework source code (src-layout)
└── tests/                  # Test suite (pytest, typed test cases)
```

---

## Getting Started

### Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) (recommended for high-speed dependency resolution and virtual environment management)

### Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/amara-ai/amara.git
   cd amara
   ```

2. **Create and activate a virtual environment with uv**:
   ```bash
   uv venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install AMARA in editable mode with development dependencies**:
   ```bash
   uv pip install -e ".[dev]"
   ```

4. **Verify the installation**:
   ```bash
   pytest
   ruff check .
   mypy src tests
   ```

---

## Code Quality Standards

AMARA enforces high engineering standards:
- **Linting & Formatting**: Enforced via Ruff (`ruff check .`, `ruff format --check .`).
- **Type Checking**: Strict type checking via mypy (`mypy src tests`).
- **Testing**: Complete coverage requirements with pytest.
- **Timestamps**: All timestamps must be timezone-aware (UTC).

---

## Contributing

We welcome community contributions. Please review [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before submitting pull requests or issue reports.

---

## License

AMARA is licensed under the [MIT License](LICENSE).

