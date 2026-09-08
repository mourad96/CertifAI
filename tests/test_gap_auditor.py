"""Unit tests for DO-178C Table A-5 Gap Auditor."""

import unittest
from pathlib import Path

from acv_engine.core.gap_auditor import GapAuditor
from acv_engine.parsers.icd_parser import ICDParser


class TestGapAuditor(unittest.TestCase):
    def setUp(self):
        self.examples_dir = Path(__file__).parent.parent / "examples" / "flight_controller" / "inputs"
        self.icd = ICDParser.parse_file(self.examples_dir / "icd.json")
        self.auditor = GapAuditor(icd=self.icd)

    def test_audit_findings(self):
        c_file = self.examples_dir / "actuator_control.c"
        findings = self.auditor.audit_path(c_file)

        self.assertGreater(len(findings), 0)
        cats = [f.category for f in findings]

        # Must flag unbounded hardware polling
        self.assertIn("UNBOUNDED_HARDWARE_POLL", cats)
        # Must flag unhandled error register
        self.assertIn("UNHANDLED_ERROR_REGISTER", cats)
        # Must flag missing input range check
        self.assertIn("MISSING_INPUT_RANGE_CHECK", cats)
        # Must flag missing switch default
        self.assertIn("SWITCH_MISSING_DEFAULT", cats)

        # Check DO-178C objective reference in findings
        for f in findings:
            self.assertTrue(f.do178c_objective.startswith("Table A-5"))
            self.assertTrue(f.remediation)

    def test_report_generation(self):
        c_file = self.examples_dir / "actuator_control.c"
        findings = self.auditor.audit_path(c_file)
        report_md = self.auditor.generate_markdown_report(findings, target_path=str(c_file))

        self.assertIn("# DO-178C DAL A Prototype Gap & Defensive Audit Report", report_md)
        self.assertIn("CRITICAL", report_md)
        self.assertIn("Table A-5 Obj", report_md)
        self.assertIn("Required Remediation", report_md)


if __name__ == "__main__":
    unittest.main()
