"""Unit tests for Requirements-Based Test Synthesizer."""

import unittest
from pathlib import Path

from acv_engine.core.test_synthesizer import TestSynthesizer
from acv_engine.schemas.validator import validate_test_vectors


class TestTestSynthesizer(unittest.TestCase):
    def setUp(self):
        self.examples_dir = Path(__file__).parent.parent / "examples" / "flight_controller" / "inputs"
        self.llr_file = self.examples_dir / "approved_llr.json"
        self.synthesizer = TestSynthesizer()

    def test_synthesize_test_vectors(self):
        test_cases = self.synthesizer.synthesize_from_file(self.llr_file, module_prefix="ACT")
        self.assertGreater(len(test_cases), 0)

        # Must pass schema validation
        validate_test_vectors(test_cases)

        categories = {tc["test_category"] for tc in test_cases}
        self.assertIn("NOMINAL", categories)
        self.assertIn("BOUNDARY", categories)
        self.assertIn("ROBUSTNESS", categories)

        # Traceability check
        for tc in test_cases:
            self.assertTrue(tc["traces_to_llr"].startswith("LLR-ACT-"))
            self.assertTrue(tc["test_case_id"].startswith("TC-ACT-"))
            self.assertIn("inputs", tc)
            self.assertIn("expected_outputs", tc)

    def test_render_unity_c_stubs(self):
        test_cases = self.synthesizer.synthesize_from_file(self.llr_file, module_prefix="ACT")
        c_code = self.synthesizer.render_c_test_stub(
            test_cases, output_filename="test_actuator.c", target_headers=["actuator_control.h"]
        )

        self.assertIn('#include "unity.h"', c_code)
        self.assertIn('#include "actuator_control.h"', c_code)
        self.assertIn("void setUp(void)", c_code)
        self.assertIn("void tearDown(void)", c_code)
        self.assertIn("int main(void)", c_code)
        self.assertIn("UNITY_BEGIN()", c_code)
        self.assertIn("UNITY_END()", c_code)
        self.assertIn("RUN_TEST(", c_code)


if __name__ == "__main__":
    unittest.main()
