# prompt-schema-guard

[![CI](https://github.com/ZelihaArslan/prompt-schema-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/ZelihaArslan/prompt-schema-guard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A lightweight, zero-dependency Python library and CLI for validating LLM JSON outputs, enforcing structural contracts, detecting leaked secrets/PII, and generating deterministic retry prompts.

## Why `prompt-schema-guard`?

Production LLM pipelines frequently break on malformed JSON, missing fields, type drift, or accidental PII exposure. `prompt-schema-guard` sits between model responses and application logic to validate payloads deterministically and produce structured feedback for automated retries.

## Features

- **Zero Runtime Dependencies:** Built strictly on the Python standard library.
- **Markdown Fence Extraction:** Automatically extracts JSON payloads wrapped in ` ```json ` blocks.
- **Strict Type & Constraint Checks:** Validates required keys, field types, allowed enums, numeric ranges, and regex patterns.
- **Built-in Security & PII Guardrails:** Flags accidental API keys, emails, or custom forbidden patterns before downstream ingestion.
- **Actionable Retry Hints:** Generates concise correction prompts to feed back into an LLM retry loop.
- **CLI Support:** Validate model outputs directly inside CI pipelines or shell scripts.

## Installation

```bash
pip install -e ".[dev]"
```

## CLI Usage

```bash
prompt-schema-guard --schema examples/schema.json --input examples/sample_output.txt
```

## License

MIT
