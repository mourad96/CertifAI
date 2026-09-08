"""Unit tests for Candidate LLR Synthesizer."""

import unittest
from pathlib import Path

from acv_engine.core.llr_synthesizer import LLRSynthesizer
from acv_engine.parsers.hlr_parser import HLRParser
from acv_engine.schemas.validator import validate_llr


class TestLLRSynthesizer(unittest.TestCase):
    def setUp(self):
        self.examples_dir = Path(__file__).parent.parent / "examples" / "flight_controller"
        self.hlr_doc = HLRParser.parse_file(self.examples_dir / "hlr.json")
        self.synthesizer = LLRSynthesizer(hlr_doc=self.hlr_doc)

    def test_synthesize_candidate_llrs(self):
        c_file = self.examples_dir / "actuator_control.c"
        h_file = self.examples_dir / "actuator_control.h"

        candidates = self.synthesizer.synthesize_from_file(c_path=c_file, header_path=h_file, module_prefix="ACT")
        self.assertEqual(len(candidates), 3)

        # Must pass schema validation
        validate_llr(candidates)

        by_fn = {c["target_function"]: c for c in candidates}

        # 1. actuator_set_position maps to HLR-ACT-001
        pos_llr = by_fn["actuator_set_position"]
        self.assertEqual(pos_llr["parent_hlr_ref"], "HLR-ACT-001")
        self.assertFalse(pos_llr["derived_requirement"])
        self.assertIn("The software shall", pos_llr["statement"])
        self.assertNotIn("for loop", pos_llr["statement"].lower())
        self.assertIn("channel", pos_llr["boundary_definitions"])

        # 2. actuator_apply_rate_filter has NO parent HLR -> derived requirement
        rate_llr = by_fn["actuator_apply_rate_filter"]
        self.assertTrue(rate_llr["derived_requirement"])
        self.assertIn("CANDIDATE_DERIVED_REQUIREMENT", rate_llr["rationale"])

        # 3. actuator_switch_mode maps to HLR-ACT-002
        mode_llr = by_fn["actuator_switch_mode"]
        self.assertEqual(mode_llr["parent_hlr_ref"], "HLR-ACT-002")
        self.assertFalse(mode_llr["derived_requirement"])


if __name__ == "__main__":
    unittest.main()
