# Contributing to `prompt-schema-guard`

Thank you for your interest in contributing! This project follows a lightweight, test-driven maintenance workflow.

## Local Development Setup

```bash
git clone https://github.com/ZelihaArslan/prompt-schema-guard.git
cd prompt-schema-guard
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Pull Request Checklist

1. **Keep Dependencies Zero:** Runtime code under `src/` must rely only on the Python standard library.
2. **Add Unit Tests:** Every new rule, CLI flag, or bug fix must include tests under `tests/`.
3. **Pass Linting & Tests:**
   ```bash
   ruff check src tests
   pytest
   ```
4. **Describe Edge Cases:** Clearly explain what malformed input or guardrail case your PR addresses.
