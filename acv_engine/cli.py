"""Command Line Interface for ACV-SE (CertifAI)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from acv_engine import __version__
from acv_engine.config import ACVConfig
from acv_engine.core.gap_auditor import GapAuditor
from acv_engine.core.llr_synthesizer import LLRSynthesizer
from acv_engine.core.test_synthesizer import TestSynthesizer
from acv_engine.parsers.hlr_parser import HLRParser
from acv_engine.parsers.icd_parser import ICDParser
from acv_engine.schemas.validator import SchemaValidationError


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="acv",
        description="Avionics Contract & Verification Synthesis Engine (ACV-SE) - DO-178C DAL A Copilot",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: audit
    audit_cmd = subparsers.add_parser(
        "audit", help="Audit prototype C source code against Hardware ICD and DO-178C Table A-5"
    )
    audit_cmd.add_argument(
        "--code", required=True, type=str, help="Path to prototype C source file or directory"
    )
    audit_cmd.add_argument(
        "--icd", required=True, type=str, help="Path to Hardware ICD JSON/YAML file"
    )
    audit_cmd.add_argument(
        "--out", default="GAP_REPORT.md", type=str, help="Path to output markdown report (default: GAP_REPORT.md)"
    )
    audit_cmd.add_argument(
        "--provider", default="auto", choices=["auto", "gemini", "openai", "anthropic", "offline"],
        help="LLM provider (default: auto)"
    )
    audit_cmd.add_argument(
        "--model", default="gemini-2.5-flash", help="LLM model identifier (default: gemini-2.5-flash)"
    )

    # Command: synthesize-llr
    llr_cmd = subparsers.add_parser(
        "synthesize-llr", help="Synthesize formal candidate LLRs from prototype code and allocated HLRs"
    )
    llr_cmd.add_argument(
        "--code", required=True, type=str, help="Path to prototype C source file"
    )
    llr_cmd.add_argument(
        "--header", default=None, type=str, help="Optional path to associated C header file"
    )
    llr_cmd.add_argument(
        "--hlr", required=True, type=str, help="Path to allocated High-Level Requirements JSON/YAML"
    )
    llr_cmd.add_argument(
        "--out", required=True, type=str, help="Output path for synthesized Candidate LLR JSON"
    )
    llr_cmd.add_argument(
        "--prefix", default="ACT", help="Module requirement prefix (e.g. ACT, NAV, SEN)"
    )
    llr_cmd.add_argument(
        "--provider", default="auto", choices=["auto", "gemini", "openai", "anthropic", "offline"],
        help="LLM provider (default: auto)"
    )
    llr_cmd.add_argument(
        "--model", default="gemini-2.5-flash", help="LLM model identifier (default: gemini-2.5-flash)"
    )

    # Command: generate-tests
    test_cmd = subparsers.add_parser(
        "generate-tests", help="Generate requirements-based test vectors and C unit test stubs"
    )
    test_cmd.add_argument(
        "--llr", required=True, type=str, help="Path to human-baselined LLR JSON file"
    )
    test_cmd.add_argument(
        "--out", required=True, type=str, help="Output path for generated C unit test harness stubs"
    )
    test_cmd.add_argument(
        "--vectors", default=None, type=str, help="Optional output path to save raw test vectors JSON"
    )
    test_cmd.add_argument(
        "--matrix", default=None, type=str,
        help="Optional output path for human-readable Markdown test vector & MC/DC table (default: companion .md next to --vectors)"
    )
    test_cmd.add_argument(
        "--target-header", default=None, action="append", help="Header file to include in generated C test stub"
    )
    test_cmd.add_argument(
        "--prefix", default="ACT", help="Module test prefix (e.g. ACT, NAV, SEN)"
    )
    test_cmd.add_argument(
        "--provider", default="auto", choices=["auto", "gemini", "openai", "anthropic", "offline"],
        help="LLM provider (default: auto)"
    )
    test_cmd.add_argument(
        "--model", default="gemini-2.5-flash", help="LLM model identifier (default: gemini-2.5-flash)"
    )

    return parser


def run_audit(args: argparse.Namespace) -> int:
    code_path = Path(args.code)
    icd_path = Path(args.icd)
    out_path = Path(args.out)

    if not code_path.exists():
        print(f"Error: Source code path does not exist: {code_path}", file=sys.stderr)
        return 1
    if not icd_path.exists():
        print(f"Error: ICD path does not exist: {icd_path}", file=sys.stderr)
        return 1

    try:
        icd_doc = ICDParser.parse_file(icd_path)
    except SchemaValidationError as e:
        print(f"Schema Error in ICD: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error reading ICD file: {e}", file=sys.stderr)
        return 1

    cfg = ACVConfig(provider=args.provider, model_name=args.model)
    auditor = GapAuditor(icd=icd_doc, config=cfg)
    findings = auditor.audit_path(code_path)
    report_md = auditor.generate_markdown_report(findings, target_path=str(code_path))

    out_path.write_text(report_md, encoding="utf-8")

    crit_count = sum(1 for f in findings if f.severity == "CRITICAL")
    high_count = sum(1 for f in findings if f.severity == "HIGH")
    med_count = sum(1 for f in findings if f.severity == "MEDIUM")
    low_count = sum(1 for f in findings if f.severity == "LOW")

    print(f"[ACV Audit Completed]")
    print(f"  Target: {code_path}")
    print(f"  Findings: {len(findings)} total (CRITICAL: {crit_count}, HIGH: {high_count}, MEDIUM: {med_count}, LOW: {low_count})")
    print(f"  Report written to: {out_path}")
    return 0


def run_synthesize_llr(args: argparse.Namespace) -> int:
    code_path = Path(args.code)
    hlr_path = Path(args.hlr)
    header_path = Path(args.header) if args.header else None
    out_path = Path(args.out)

    if not code_path.exists():
        print(f"Error: Source code path does not exist: {code_path}", file=sys.stderr)
        return 1
    if not hlr_path.exists():
        print(f"Error: HLR path does not exist: {hlr_path}", file=sys.stderr)
        return 1

    try:
        hlr_doc = HLRParser.parse_file(hlr_path)
    except SchemaValidationError as e:
        print(f"Schema Error in HLR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error reading HLR file: {e}", file=sys.stderr)
        return 1

    cfg = ACVConfig(provider=args.provider, model_name=args.model)
    synthesizer = LLRSynthesizer(hlr_doc=hlr_doc, config=cfg)

    try:
        candidates = synthesizer.synthesize_from_file(
            c_path=code_path, header_path=header_path, module_prefix=args.prefix
        )
    except SchemaValidationError as e:
        print(f"Candidate LLR Schema Validation Failed: {e}", file=sys.stderr)
        return 1

    out_path.write_text(json.dumps(candidates, indent=2), encoding="utf-8")
    derived_count = sum(1 for c in candidates if c.get("derived_requirement"))

    print(f"[ACV LLR Synthesis Completed]")
    print(f"  Source: {code_path}")
    print(f"  Synthesized LLRs: {len(candidates)} (Derived: {derived_count})")
    print(f"  Output written to: {out_path}")
    return 0


def run_generate_tests(args: argparse.Namespace) -> int:
    llr_path = Path(args.llr)
    out_path = Path(args.out)
    vectors_path = Path(args.vectors) if args.vectors else None
    matrix_path = Path(args.matrix) if getattr(args, "matrix", None) else None

    # If --matrix not explicitly provided, but --vectors is given, auto-generate companion .md
    if not matrix_path and vectors_path:
        matrix_path = vectors_path.with_suffix(".md")

    if not llr_path.exists():
        print(f"Error: LLR path does not exist: {llr_path}", file=sys.stderr)
        return 1

    cfg = ACVConfig(provider=args.provider, model_name=args.model)
    synthesizer = TestSynthesizer(config=cfg)

    try:
        test_cases = synthesizer.synthesize_from_file(llr_file=llr_path, module_prefix=args.prefix)
    except SchemaValidationError as e:
        print(f"Test Vector Schema Validation Failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error generating test specifications: {e}", file=sys.stderr)
        return 1

    # Optionally write raw test vectors JSON
    if vectors_path:
        vectors_path.parent.mkdir(parents=True, exist_ok=True)
        vectors_path.write_text(json.dumps(test_cases, indent=2), encoding="utf-8")

    # Load baselined LLRs for MC/DC analysis if readable
    llr_list = None
    try:
        raw_llr = json.loads(llr_path.read_text(encoding="utf-8"))
        llr_list = raw_llr.get("items", raw_llr) if isinstance(raw_llr, dict) else raw_llr
    except Exception:
        pass

    # Render and write human-readable Markdown test matrix & MC/DC table
    if matrix_path:
        matrix_path.parent.mkdir(parents=True, exist_ok=True)
        matrix_md = synthesizer.generate_markdown_matrix(
            test_cases=test_cases,
            llr_list=llr_list,
            module_prefix=args.prefix,
        )
        matrix_path.write_text(matrix_md, encoding="utf-8")

    # Render C Unity test stubs
    c_stubs = synthesizer.render_c_test_stub(
        test_cases=test_cases,
        output_filename=out_path.name,
        target_headers=args.target_header or [],
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(c_stubs, encoding="utf-8")

    nom_count = sum(1 for t in test_cases if t["test_category"] == "NOMINAL")
    bnd_count = sum(1 for t in test_cases if t["test_category"] == "BOUNDARY")
    rob_count = sum(1 for t in test_cases if t["test_category"] == "ROBUSTNESS")

    print(f"[ACV Test Scaffolding Completed]")
    print(f"  LLRs Traced: {llr_path}")
    print(f"  Total Test Cases: {len(test_cases)} (Nominal: {nom_count}, Boundary: {bnd_count}, Robustness: {rob_count})")
    print(f"  C Test Harness Stub: {out_path}")
    if vectors_path:
        print(f"  Test Vectors JSON: {vectors_path}")
    if matrix_path:
        print(f"  Test Matrix (MC/DC Table): {matrix_path}")
    return 0


def main(argv=None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "audit":
        return run_audit(args)
    elif args.command == "synthesize-llr":
        return run_synthesize_llr(args)
    elif args.command == "generate-tests":
        return run_generate_tests(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
