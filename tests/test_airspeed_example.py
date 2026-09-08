"""Unit and integration tests for airspeed sensor example."""

import unittest
from pathlib import Path

from acv_engine.core.gap_auditor import GapAuditor
from acv_engine.core.llr_synthesizer import LLRSynthesizer
from acv_engine.core.test_synthesizer import TestSynthesizer
from acv_engine.parsers.c_ast_parser import CASTParser
from acv_engine.parsers.hlr_parser import HLRParser
from acv_engine.parsers.icd_parser import ICDParser
from acv_engine.schemas.validator import validate_llr, validate_test_vectors


class TestAirspeedSensorExample(unittest.TestCase):
    def setUp(self):
        self.inputs_dir = Path(__file__).parent.parent / "examples" / "airspeed_sensor" / "inputs"
        self.c_file = self.inputs_dir / "airspeed_sensor.c"
        self.h_file = self.inputs_dir / "airspeed_sensor.h"
        self.hlr_file = self.inputs_dir / "hlr.json"
        self.icd_file = self.inputs_dir / "icd.json"
        self.llr_file = self.inputs_dir / "approved_llr.json"

    def test_airspeed_parsers(self):
        parser = CASTParser(known_registers={"AIRSPEED_STATUS_REG", "AIRSPEED_DATA_REG"})
        parsed = parser.parse_file(self.c_file)
        fn_names = [f.name for f in parsed.functions]
        self.assertIn("airspeed_read_knots", fn_names)
        self.assertIn("airspeed_celsius_to_kelvin", fn_names)

        hlr_doc = HLRParser.parse_file(self.hlr_file)
        self.assertEqual(len(hlr_doc.items), 1)
        self.assertEqual(hlr_doc.items[0].hlr_id, "HLR-IAS-001")

        icd_doc = ICDParser.parse_file(self.icd_file)
        self.assertEqual(icd_doc.device_name, "Pitot_Static_Airspeed_Transducer")
        status_reg = icd_doc.get_register("AIRSPEED_STATUS_REG")
        self.assertIsNotNone(status_reg)
        self.assertEqual(status_reg.ready_mask, "0x00000001")
        self.assertEqual(status_reg.error_mask, "0x00000002")

    def test_airspeed_gap_audit(self):
        icd_doc = ICDParser.parse_file(self.icd_file)
        auditor = GapAuditor(icd=icd_doc)
        findings = auditor.audit_path(self.c_file)

        self.assertGreater(len(findings), 0)
        categories = [f.category for f in findings]
        self.assertIn("UNBOUNDED_HARDWARE_POLL", categories)
        self.assertIn("UNHANDLED_ERROR_REGISTER", categories)
        self.assertIn("MISSING_INPUT_RANGE_CHECK", categories)

    def test_airspeed_llr_synthesis(self):
        hlr_doc = HLRParser.parse_file(self.hlr_file)
        synthesizer = LLRSynthesizer(hlr_doc=hlr_doc)
        candidates = synthesizer.synthesize_from_file(self.c_file, header_path=self.h_file, module_prefix="IAS")

        validate_llr(candidates)
        by_fn = {c["target_function"]: c for c in candidates}
        self.assertIn("airspeed_read_knots", by_fn)
        # Helper function with no parent HLR must be flagged as derived
        self.assertIn("airspeed_celsius_to_kelvin", by_fn)
        self.assertTrue(by_fn["airspeed_celsius_to_kelvin"]["derived_requirement"])

    def test_airspeed_test_synthesis(self):
        synthesizer = TestSynthesizer()
        test_cases = synthesizer.synthesize_from_file(self.llr_file, module_prefix="IAS")

        validate_test_vectors(test_cases)
        categories = {tc["test_category"] for tc in test_cases}
        self.assertIn("NOMINAL", categories)
        self.assertIn("BOUNDARY", categories)
        self.assertIn("ROBUSTNESS", categories)


if __name__ == "__main__":
    unittest.main()
