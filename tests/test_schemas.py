"""Unit tests for JSON Schemas and Schema Validation."""

import unittest
from acv_engine.schemas.validator import (
    validate_hlr,
    validate_llr,
    validate_test_vectors,
    validate_icd,
    SchemaValidationError,
)


class TestSchemas(unittest.TestCase):
    def test_valid_hlr(self):
        valid_hlrs = [
            {
                "hlr_id": "HLR-NAV-001",
                "description": "The system shall read GPS telemetry every 20ms.",
                "safety_impact": "CAT",
                "interfaces": ["gps_uart_rx"],
            }
        ]
        validate_hlr(valid_hlrs)

    def test_invalid_hlr_id_pattern(self):
        invalid_hlrs = [
            {
                "hlr_id": "INVALID-ID",
                "description": "Some description",
                "safety_impact": "CAT",
            }
        ]
        with self.assertRaises(SchemaValidationError):
            validate_hlr(invalid_hlrs)

    def test_invalid_hlr_safety_impact(self):
        invalid_hlrs = [
            {
                "hlr_id": "HLR-NAV-001",
                "description": "Some description",
                "safety_impact": "UNKNOWN_SEVERITY",
            }
        ]
        with self.assertRaises(SchemaValidationError):
            validate_hlr(invalid_hlrs)

    def test_valid_candidate_llr(self):
        valid_llrs = [
            {
                "llr_id": "LLR-ACT-0001",
                "parent_hlr_ref": "HLR-ACT-001",
                "target_function": "actuator_set_position",
                "pre_conditions": ["Hardware ready bit asserted."],
                "statement": "The software shall set servo position.",
                "post_conditions": ["Returns ACT_OK."],
                "boundary_definitions": {"angle": "-45 to +45"},
                "derived_requirement": False,
                "rationale": "Directly traces to HLR-ACT-001.",
            }
        ]
        validate_llr(valid_llrs)

    def test_invalid_candidate_llr_missing_statement(self):
        invalid_llrs = [
            {
                "llr_id": "LLR-ACT-0001",
                "parent_hlr_ref": "HLR-ACT-001",
                "target_function": "actuator_set_position",
                "derived_requirement": False,
            }
        ]
        with self.assertRaises(SchemaValidationError):
            validate_llr(invalid_llrs)

    def test_valid_test_vector(self):
        valid_vectors = [
            {
                "test_case_id": "TC-ACT-0001",
                "traces_to_llr": "LLR-ACT-0001",
                "test_category": "NOMINAL",
                "description": "Nominal servo angle command.",
                "inputs": {"angle": 10.0},
                "expected_outputs": {"status": "SUCCESS"},
                "fault_injection": None,
            }
        ]
        validate_test_vectors(valid_vectors)

    def test_invalid_test_vector_category(self):
        invalid_vectors = [
            {
                "test_case_id": "TC-ACT-0001",
                "traces_to_llr": "LLR-ACT-0001",
                "test_category": "EXPLORATORY",  # Invalid category
                "inputs": {},
                "expected_outputs": {},
            }
        ]
        with self.assertRaises(SchemaValidationError):
            validate_test_vectors(invalid_vectors)

    def test_valid_icd(self):
        valid_icd = {
            "device_name": "Test_Device",
            "registers": [
                {
                    "name": "TEST_REG",
                    "address": "0x1000",
                    "ready_mask": "0x01",
                }
            ],
        }
        validate_icd(valid_icd)


if __name__ == "__main__":
    unittest.main()
