"""JSON Schema validation utilities for ACV-SE."""

import json
from pathlib import Path
from typing import Any, Dict, List, Union
import jsonschema

SCHEMA_DIR = Path(__file__).parent


class SchemaValidationError(Exception):
    """Raised when JSON data violates DO-178C artifact schemas."""

    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or []


def _load_schema(filename: str) -> Dict[str, Any]:
    schema_path = SCHEMA_DIR / filename
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


HLR_SCHEMA = _load_schema("hlr_schema.json")
LLR_CANDIDATE_SCHEMA = _load_schema("llr_candidate_schema.json")
TEST_VECTOR_SCHEMA = _load_schema("test_vector_schema.json")
ICD_SCHEMA = _load_schema("icd_schema.json")


def _validate(data: Any, schema: Dict[str, Any], schema_name: str) -> None:
    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors(data))
    if errors:
        error_msgs = []
        for err in errors:
            path_str = " -> ".join([str(p) for p in err.path]) or "root"
            error_msgs.append(f"[{path_str}]: {err.message}")
        full_msg = f"Validation failed for {schema_name}:\n" + "\n".join(f"  - {m}" for m in error_msgs)
        raise SchemaValidationError(full_msg, errors=error_msgs)


def validate_hlr(data: Any) -> None:
    """Validate High-Level Requirements list against hlr_schema.json."""
    _validate(data, HLR_SCHEMA, "HLR Specification")


def validate_llr(data: Any) -> None:
    """Validate Candidate Low-Level Requirements list against llr_candidate_schema.json."""
    _validate(data, LLR_CANDIDATE_SCHEMA, "LLR Specification")


def validate_test_vectors(data: Any) -> None:
    """Validate Test Specifications against test_vector_schema.json."""
    _validate(data, TEST_VECTOR_SCHEMA, "Test Specification")


def validate_icd(data: Any) -> None:
    """Validate Hardware Interface Control Document against icd_schema.json."""
    _validate(data, ICD_SCHEMA, "Hardware ICD")
