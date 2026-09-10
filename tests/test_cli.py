"""End-to-End CLI tests for ACV-SE."""

import json
import tempfile
import unittest
from pathlib import Path

from acv_engine.cli import main
from acv_engine.schemas.validator import validate_llr, validate_test_vectors


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.examples_dir = Path(__file__).parent.parent / "examples" / "flight_controller" / "inputs"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_help(self):
        with self.assertRaises(SystemExit) as cm:
            main(["--help"])
        self.assertEqual(cm.exception.code, 0)

    def test_cli_audit(self):
        c_file = str(self.examples_dir / "actuator_control.c")
        icd_file = str(self.examples_dir / "icd.json")
        out_report = str(self.temp_path / "GAP_REPORT.md")

        ret = main(["audit", "--code", c_file, "--icd", icd_file, "--out", out_report, "--provider", "offline"])
        self.assertEqual(ret, 0)
        self.assertTrue(Path(out_report).exists())

        content = Path(out_report).read_text(encoding="utf-8")
        self.assertIn("# DO-178C DAL A Prototype Gap & Defensive Audit Report", content)
        self.assertIn("CRITICAL", content)

    def test_cli_synthesize_llr(self):
        c_file = str(self.examples_dir / "actuator_control.c")
        h_file = str(self.examples_dir / "actuator_control.h")
        hlr_file = str(self.examples_dir / "hlr.json")
        out_json = str(self.temp_path / "candidates.json")

        ret = main([
            "synthesize-llr",
            "--code", c_file,
            "--header", h_file,
            "--hlr", hlr_file,
            "--out", out_json,
            "--prefix", "ACT",
            "--provider", "offline",
        ])
        self.assertEqual(ret, 0)
        self.assertTrue(Path(out_json).exists())

        candidates = json.loads(Path(out_json).read_text(encoding="utf-8"))
        validate_llr(candidates)
        self.assertEqual(len(candidates), 3)

    def test_cli_generate_tests(self):
        llr_file = str(self.examples_dir / "approved_llr.json")
        out_c = str(self.temp_path / "test_stubs.c")
        out_vectors = str(self.temp_path / "vectors.json")

        ret = main([
            "generate-tests",
            "--llr", llr_file,
            "--out", out_c,
            "--vectors", out_vectors,
            "--prefix", "ACT",
            "--provider", "offline",
        ])
        self.assertEqual(ret, 0)
        self.assertTrue(Path(out_c).exists())
        self.assertTrue(Path(out_vectors).exists())
        # Verify companion Markdown table was automatically created alongside .json
        out_matrix = self.temp_path / "vectors.md"
        self.assertTrue(out_matrix.exists())
        matrix_text = out_matrix.read_text(encoding="utf-8")
        self.assertIn("# DO-178C DAL A Requirements-Based Test Matrix & MC/DC Analysis", matrix_text)
        self.assertIn("MC/DC", matrix_text)

        vectors = json.loads(Path(out_vectors).read_text(encoding="utf-8"))
        validate_test_vectors(vectors)

        c_text = Path(out_c).read_text(encoding="utf-8")
        self.assertIn("RUN_TEST", c_text)
        self.assertIn("UNITY_BEGIN", c_text)

    def test_cli_generate_tests_explicit_matrix(self):
        llr_file = str(self.examples_dir / "approved_llr.json")
        out_c = str(self.temp_path / "test_stubs2.c")
        out_matrix = str(self.temp_path / "custom_matrix.md")

        ret = main([
            "generate-tests",
            "--llr", llr_file,
            "--out", out_c,
            "--matrix", out_matrix,
            "--prefix", "ACT",
            "--provider", "offline",
        ])
        self.assertEqual(ret, 0)
        self.assertTrue(Path(out_c).exists())
        self.assertTrue(Path(out_matrix).exists())
        matrix_text = Path(out_matrix).read_text(encoding="utf-8")
        self.assertIn("# DO-178C DAL A Requirements-Based Test Matrix & MC/DC Analysis", matrix_text)


if __name__ == "__main__":
    unittest.main()
