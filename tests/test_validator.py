import json
from pathlib import Path

from prompt_schema_guard import FieldSpec, SchemaGuard
from prompt_schema_guard.cli import main as cli_main


def test_valid_markdown_fenced_json():
    guard = SchemaGuard(
        fields={
            "category": FieldSpec(expected_type=str, choices=["bug", "feature"]),
            "priority": FieldSpec(expected_type=int, min_value=1, max_value=5),
        }
    )
    raw = """Here is the result:
```json
{
  "category": "bug",
  "priority": 2
}
```"""
    result = guard.validate(raw)
    assert result.is_valid is True
    assert result.data == {"category": "bug", "priority": 2}
    assert result.retry_prompt == ""


def test_bool_does_not_pass_as_int():
    guard = SchemaGuard(fields={"count": FieldSpec(expected_type=int)})
    result = guard.validate('{"count": true}')
    assert result.is_valid is False
    assert any("expected type 'int'" in err for err in result.errors)


def test_pii_detection_blocks_email_and_secret():
    guard = SchemaGuard(fields={"note": FieldSpec(expected_type=str)}, block_pii=True)
    result = guard.validate('{"note": "Contact admin@example.com with sk-1234567890abcdefghij"}')
    assert result.is_valid is False
    assert len(result.errors) == 2
    assert "failed schema validation" in result.retry_prompt


def test_cli_end_to_end(tmp_path: Path):
    schema_file = tmp_path / "schema.json"
    input_file = tmp_path / "output.txt"

    schema_file.write_text(
        json.dumps(
            {
                "fields": {
                    "status": {"type": "str", "choices": ["ok", "fail"]},
                    "score": {"type": "float", "min_value": 0.0, "max_value": 1.0},
                }
            }
        ),
        encoding="utf-8",
    )
    input_file.write_text('{"status": "ok", "score": 0.88}', encoding="utf-8")

    exit_code = cli_main(["--schema", str(schema_file), "--input", str(input_file)])
    assert exit_code == 0
