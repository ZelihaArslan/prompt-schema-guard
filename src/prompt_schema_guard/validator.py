from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, Union

_FENCE_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

DEFAULT_PII_PATTERNS: Dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}


@dataclass(frozen=True)
class FieldSpec:
    """Contract definition for a single JSON object field."""

    expected_type: Union[Type[Any], Tuple[Type[Any], ...]]
    required: bool = True
    choices: Optional[Sequence[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    custom_validator: Optional[Callable[[Any], Optional[str]]] = None


@dataclass
class ValidationResult:
    """Outcome of validating an LLM response against a SchemaGuard."""

    is_valid: bool
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)

    @property
    def retry_prompt(self) -> str:
        """Generates a deterministic correction instruction for LLM retries."""
        if self.is_valid:
            return ""
        bullet_list = "\n".join(f"- {err}" for err in self.errors)
        return (
            "Your previous response failed schema validation. "
            "Return ONLY a valid JSON object fixing these issues:\n"
            f"{bullet_list}"
        )


class SchemaGuard:
    """Validates raw LLM string responses against strict field and guardrail rules."""

    def __init__(
        self,
        fields: Dict[str, FieldSpec],
        allow_extra_fields: bool = False,
        block_pii: bool = True,
        extra_forbidden_patterns: Optional[Dict[str, str]] = None,
    ) -> None:
        self.fields = fields
        self.allow_extra_fields = allow_extra_fields
        self.block_pii = block_pii
        self.forbidden_patterns: Dict[str, re.Pattern[str]] = {}
        if block_pii:
            self.forbidden_patterns.update(DEFAULT_PII_PATTERNS)
        if extra_forbidden_patterns:
            for name, raw_regex in extra_forbidden_patterns.items():
                self.forbidden_patterns[name] = re.compile(raw_regex)

    @staticmethod
    def extract_json_text(raw_text: str) -> str:
        """Extracts JSON payload from markdown fences if present."""
        stripped = raw_text.strip()
        match = _FENCE_PATTERN.search(stripped)
        if match:
            return match.group(1).strip()
        return stripped

    def _check_type(self, value: Any, expected: Union[Type[Any], Tuple[Type[Any], ...]]) -> bool:
        if isinstance(value, bool):
            if expected is bool:
                return True
            if isinstance(expected, tuple) and bool in expected:
                return True
            return False
        if expected is float and isinstance(value, int):
            return True
        return isinstance(value, expected)

    def _scan_forbidden_patterns(self, payload_text: str) -> List[str]:
        violations: List[str] = []
        for rule_name, regex in self.forbidden_patterns.items():
            if regex.search(payload_text):
                violations.append(f"Guardrail violation: detected forbidden pattern '{rule_name}'.")
        return violations

    def validate(self, raw_response: str) -> ValidationResult:
        errors: List[str] = []
        cleaned_text = self.extract_json_text(raw_response)

        if self.forbidden_patterns:
            errors.extend(self._scan_forbidden_patterns(cleaned_text))

        try:
            parsed = json.loads(cleaned_text)
        except json.JSONDecodeError as exc:
            errors.insert(0, f"Invalid JSON syntax at line {exc.lineno}, column {exc.colno}: {exc.msg}.")
            return ValidationResult(is_valid=False, data=None, errors=errors)

        if not isinstance(parsed, dict):
            errors.insert(0, f"Root JSON value must be an object, got {type(parsed).__name__}.")
            return ValidationResult(is_valid=False, data=None, errors=errors)

        if not self.allow_extra_fields:
            unknown_keys = sorted(set(parsed.keys()) - set(self.fields.keys()))
            for key in unknown_keys:
                errors.append(f"Unexpected field '{key}' is not allowed by schema.")

        for name, spec in self.fields.items():
            if name not in parsed or parsed[name] is None:
                if spec.required:
                    errors.append(f"Missing required field '{name}'.")
                continue

            value = parsed[name]
            if not self._check_type(value, spec.expected_type):
                expected_name = (
                    ", ".join(t.__name__ for t in spec.expected_type)
                    if isinstance(spec.expected_type, tuple)
                    else spec.expected_type.__name__
                )
                errors.append(
                    f"Field '{name}' expected type '{expected_name}', got '{type(value).__name__}'."
                )
                continue

            if spec.choices is not None and value not in spec.choices:
                errors.append(f"Field '{name}' must be one of {list(spec.choices)}, got {value!r}.")

            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if spec.min_value is not None and value < spec.min_value:
                    errors.append(f"Field '{name}' must be >= {spec.min_value}, got {value}.")
                if spec.max_value is not None and value > spec.max_value:
                    errors.append(f"Field '{name}' must be <= {spec.max_value}, got {value}.")

            if isinstance(value, (str, list, dict)):
                if spec.min_length is not None and len(value) < spec.min_length:
                    errors.append(
                        f"Field '{name}' length must be >= {spec.min_length}, got {len(value)}."
                    )
                if spec.max_length is not None and len(value) > spec.max_length:
                    errors.append(
                        f"Field '{name}' length must be <= {spec.max_length}, got {len(value)}."
                    )

            if isinstance(value, str) and spec.pattern is not None:
                if not re.search(spec.pattern, value):
                    errors.append(f"Field '{name}' does not match required pattern '{spec.pattern}'.")

            if spec.custom_validator is not None:
                custom_err = spec.custom_validator(value)
                if custom_err:
                    errors.append(f"Field '{name}': {custom_err}")

        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, data=parsed if is_valid else None, errors=errors)
