from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Type

from .validator import FieldSpec, SchemaGuard

TYPE_MAP: Dict[str, Type[Any]] = {
    "str": str,
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "number": float,
    "bool": bool,
    "boolean": bool,
    "list": list,
    "array": list,
    "dict": dict,
    "object": dict,
}


def load_guard_from_schema_file(schema_path: Path) -> SchemaGuard:
    raw = json.loads(schema_path.read_text(encoding="utf-8"))
    fields: Dict[str, FieldSpec] = {}

    for field_name, cfg in raw.get("fields", {}).items():
        type_key = cfg.get("type", "str").lower()
        if type_key not in TYPE_MAP:
            raise ValueError(f"Unsupported type '{type_key}' for field '{field_name}'.")
        fields[field_name] = FieldSpec(
            expected_type=TYPE_MAP[type_key],
            required=cfg.get("required", True),
            choices=cfg.get("choices"),
            min_value=cfg.get("min_value"),
            max_value=cfg.get("max_value"),
            min_length=cfg.get("min_length"),
            max_length=cfg.get("max_length"),
            pattern=cfg.get("pattern"),
        )

    return SchemaGuard(
        fields=fields,
        allow_extra_fields=raw.get("allow_extra_fields", False),
        block_pii=raw.get("block_pii", True),
        extra_forbidden_patterns=raw.get("extra_forbidden_patterns"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prompt-schema-guard",
        description="Validate LLM output text against a JSON schema contract.",
    )
    parser.add_argument("--schema", required=True, type=Path, help="Path to JSON schema config.")
    parser.add_argument("--input", required=True, type=Path, help="Path to raw LLM output file.")
    args = parser.parse_args(argv)

    guard = load_guard_from_schema_file(args.schema)
    raw_output = args.input.read_text(encoding="utf-8")
    result = guard.validate(raw_output)

    if result.is_valid:
        print(json.dumps({"status": "valid", "data": result.data}, indent=2))
        return 0

    print(
        json.dumps(
            {
                "status": "invalid",
                "errors": result.errors,
                "retry_prompt": result.retry_prompt,
            },
            indent=2,
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
