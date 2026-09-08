"""Unit tests for AST, HLR, and ICD Parsers."""

import unittest
from pathlib import Path

from acv_engine.parsers.c_ast_parser import CASTParser
from acv_engine.parsers.hlr_parser import HLRParser
from acv_engine.parsers.icd_parser import ICDParser


class TestParsers(unittest.TestCase):
    def setUp(self):
        self.examples_dir = Path(__file__).parent.parent / "examples" / "flight_controller"

    def test_c_ast_parser_functions(self):
        c_file = self.examples_dir / "actuator_control.c"
        parser = CASTParser(known_registers={"ACT_STATUS_REG", "ACT_CTRL_REG", "ACT_POS_REG"})
        parsed = parser.parse_file(c_file)

        fn_names = [f.name for f in parsed.functions]
        self.assertIn("actuator_set_position", fn_names)
        self.assertIn("actuator_apply_rate_filter", fn_names)
        self.assertIn("actuator_switch_mode", fn_names)

        # Inspect actuator_set_position
        set_pos_fn = next(f for f in parsed.functions if f.name == "actuator_set_position")
        self.assertEqual(len(set_pos_fn.parameters), 2)
        self.assertEqual(set_pos_fn.parameters[0].name, "channel")
        self.assertEqual(set_pos_fn.parameters[1].name, "target_angle_deg")

        # Inspect loop detection
        self.assertEqual(len(set_pos_fn.loops), 1)
        loop = set_pos_fn.loops[0]
        self.assertEqual(loop.loop_type, "while")
        self.assertTrue(loop.polls_hardware)
        self.assertFalse(loop.has_timeout_or_break)

        # Inspect switch missing default in actuator_switch_mode
        switch_fn = next(f for f in parsed.functions if f.name == "actuator_switch_mode")
        self.assertEqual(len(switch_fn.switches_missing_default), 1)

    def test_hlr_parser(self):
        hlr_file = self.examples_dir / "hlr.json"
        hlr_doc = HLRParser.parse_file(hlr_file)

        self.assertEqual(len(hlr_doc.items), 2)
        h1 = hlr_doc.get_by_id("HLR-ACT-001")
        self.assertIsNotNone(h1)
        self.assertEqual(h1.safety_impact, "CAT")

        # Test semantic matching
        matched = hlr_doc.match_function("actuator_set_position")
        self.assertIsNotNone(matched)
        self.assertEqual(matched.hlr_id, "HLR-ACT-001")

        # Test unmapped function
        unmapped = hlr_doc.match_function("actuator_apply_rate_filter")
        self.assertIsNone(unmapped)

    def test_icd_parser(self):
        icd_file = self.examples_dir / "icd.json"
        icd_doc = ICDParser.parse_file(icd_file)

        self.assertEqual(icd_doc.device_name, "FlightSurface_Actuator_Controller")
        self.assertEqual(icd_doc.default_timeout_us, 500.0)

        status_reg = icd_doc.get_register("ACT_STATUS_REG")
        self.assertIsNotNone(status_reg)
        self.assertEqual(status_reg.ready_mask, "0x00000001")
        self.assertEqual(status_reg.error_mask, "0x00000002")


if __name__ == "__main__":
    unittest.main()
