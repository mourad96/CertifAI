"""DO-178C Table A-5 Defensive Auditing Engine."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from acv_engine.config import ACVConfig, default_config
from acv_engine.core.llm_client import LLMClient
from acv_engine.parsers.c_ast_parser import CASTParser, FunctionInfo, LoopInfo, ParsedCFile
from acv_engine.parsers.icd_parser import ICDDocument, ICDParser, RegisterDefinition
from acv_engine.prompts.gap_prompt_template import GAP_SYSTEM_PROMPT, build_gap_audit_prompt


@dataclass
class GapFinding:
    finding_id: str
    category: str
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    file_path: str
    line_number: int
    function_name: str
    do178c_objective: str
    description: str
    code_snippet: str
    remediation: str


class GapAuditor:
    """Audits prototype C source code against DO-178C Table A-5 defensive guidelines and Hardware ICD."""

    def __init__(self, icd: ICDDocument, config: Optional[ACVConfig] = None):
        self.icd = icd
        self.config = config or default_config
        self.known_regs = self.icd.get_register_names()
        self.ast_parser = CASTParser(known_registers=self.known_regs)
        self.llm_client = LLMClient(config=self.config) if self.config.resolve_provider() != "offline" else None

    def audit_path(self, code_path: Path) -> List[GapFinding]:
        """Audit a C source file or directory of C files."""
        findings: List[GapFinding] = []
        p = Path(code_path)
        if not p.exists():
            raise FileNotFoundError(f"Source code path not found: {p}")

        parsed_files: List[ParsedCFile] = []
        if p.is_file():
            parsed_files.append(self.ast_parser.parse_file(p))
        else:
            parsed_files.extend(self.ast_parser.parse_directory(p))

        counter = 1
        for pf in parsed_files:
            file_findings = self._audit_file_static(pf, counter)
            counter += len(file_findings)
            findings.extend(file_findings)

        return findings

    def _audit_file_static(self, parsed: ParsedCFile, start_idx: int) -> List[GapFinding]:
        findings: List[GapFinding] = []
        idx = start_idx

        # Check file-level register error evaluations
        file_text = parsed.raw_source

        for fn in parsed.functions:
            # 1. Audit Loops: Unbounded hardware polling and missing loop bounds
            for loop in fn.loops:
                if not loop.has_timeout_or_break:
                    is_hw_poll = loop.polls_hardware or any(
                        reg in loop.condition_text for reg in self.known_regs
                    )
                    sev = "CRITICAL" if is_hw_poll else "HIGH"
                    cat = "UNBOUNDED_HARDWARE_POLL" if is_hw_poll else "UNBOUNDED_LOOP"
                    desc = (
                        f"Unbounded hardware polling loop detected on condition '{loop.condition_text}'. "
                        f"Missing iteration limit or timeout watchdog counter."
                        if is_hw_poll
                        else f"Loop '{loop.condition_text}' has no detected timeout or bounded termination condition."
                    )
                    remediation = (
                        "Introduce a deterministic timeout counter bounded by max hardware latency "
                        f"(e.g., uint32_t timeout = {int(self.icd.default_timeout_us)}UL; while (--timeout && ...) )."
                    )

                    findings.append(
                        GapFinding(
                            finding_id=f"GAP-{idx:04d}",
                            category=cat,
                            severity=sev,
                            file_path=parsed.file_path,
                            line_number=loop.start_line,
                            function_name=fn.name,
                            do178c_objective="Table A-5 Obj 3 (Verifiable Code: Absence of Unbounded Execution)",
                            description=desc,
                            code_snippet=f"{loop.loop_type} ({loop.condition_text}) {loop.body_text[:60]}",
                            remediation=remediation,
                        )
                    )
                    idx += 1

            # 2. Audit Register Error Checks
            for reg_access in fn.register_accesses:
                reg_def = self.icd.get_register(reg_access.register_name)
                if reg_def and reg_def.error_mask:
                    # Check if the function body checks the error mask
                    err_mask_str = str(reg_def.error_mask)
                    if err_mask_str not in fn.body_source and "ERR" not in fn.body_source.upper():
                        findings.append(
                            GapFinding(
                                finding_id=f"GAP-{idx:04d}",
                                category="UNHANDLED_ERROR_REGISTER",
                                severity="CRITICAL",
                                file_path=parsed.file_path,
                                line_number=reg_access.line_number,
                                function_name=fn.name,
                                do178c_objective="Table A-5 Obj 2 (Architecture Compliance: Hardware Fault Handling)",
                                description=(
                                    f"Register '{reg_access.register_name}' has hardware error bitmask "
                                    f"({reg_def.error_mask}), but function '{fn.name}' accesses it without "
                                    "verifying error status flags."
                                ),
                                code_snippet=reg_access.expression_text,
                                remediation=(
                                    f"Evaluate error mask before proceeding: "
                                    f"if ({reg_access.register_name} & {reg_def.error_mask}) return ERR_HARDWARE_FAULT;"
                                ),
                            )
                        )
                        idx += 1

            # 3. Audit Input Parameters: Missing range assertions
            if fn.parameters and not fn.checked_parameters:
                param_str = ", ".join(f"{p.type_name} {p.name}" for p in fn.parameters)
                findings.append(
                    GapFinding(
                        finding_id=f"GAP-{idx:04d}",
                        category="MISSING_INPUT_RANGE_CHECK",
                        severity="HIGH",
                        file_path=parsed.file_path,
                        line_number=fn.start_line,
                        function_name=fn.name,
                        do178c_objective="Table A-5 Obj 1 & 4 (Robustness: Input Range Validation)",
                        description=(
                            f"Function '{fn.name}' consumes parameters ({param_str}) without defensive "
                            "pre-condition range assertions or validation before processing."
                        ),
                        code_snippet=f"{fn.return_type} {fn.name}({param_str})",
                        remediation="Add defensive boundary checks on all input parameters before execution.",
                    )
                )
                idx += 1

            # 4. Audit Arithmetic Risks: Potential overflow / divide-by-zero
            for arith in fn.arithmetic_ops:
                if arith.risk_type == "DIV_ZERO":
                    findings.append(
                        GapFinding(
                            finding_id=f"GAP-{idx:04d}",
                            category="DIVIDE_BY_ZERO_RISK",
                            severity="HIGH",
                            file_path=parsed.file_path,
                            line_number=arith.line_number,
                            function_name=fn.name,
                            do178c_objective="Table A-5 Obj 3 (Robustness: Arithmetic Anomaly Freedom)",
                            description=f"Division operator in expression '{arith.expression_text}' without explicit zero-check.",
                            code_snippet=arith.expression_text,
                            remediation="Guard divisor against zero before division operation.",
                        )
                    )
                    idx += 1
                elif arith.risk_type == "OVERFLOW":
                    findings.append(
                        GapFinding(
                            finding_id=f"GAP-{idx:04d}",
                            category="ARITHMETIC_OVERFLOW_RISK",
                            severity="MEDIUM",
                            file_path=parsed.file_path,
                            line_number=arith.line_number,
                            function_name=fn.name,
                            do178c_objective="Table A-5 Obj 3 (Robustness: Arithmetic Anomaly Freedom)",
                            description=f"Potential integer overflow risk in calculation '{arith.expression_text}'.",
                            code_snippet=arith.expression_text,
                            remediation="Ensure input operand bounds guarantee saturation or use safe saturating math routines.",
                        )
                    )
                    idx += 1

            # 5. Audit Switch statements missing default
            for line in fn.switches_missing_default:
                findings.append(
                    GapFinding(
                        finding_id=f"GAP-{idx:04d}",
                        category="SWITCH_MISSING_DEFAULT",
                        severity="MEDIUM",
                        file_path=parsed.file_path,
                        line_number=line,
                        function_name=fn.name,
                        do178c_objective="Table A-5 Obj 4 (Coding Standards: Defensive Control Flow)",
                        description=f"Switch statement in '{fn.name}' lacks a default handler clause.",
                        code_snippet=f"switch (...) in {fn.name}",
                        remediation="Add a 'default:' branch asserting unexpected state or returning an error code.",
                    )
                )
                idx += 1

        return findings

    def generate_markdown_report(self, findings: List[GapFinding], target_path: str = "") -> str:
        """Generate formatted GAP_REPORT.md conforming to DO-178C Table A-5 audit format."""
        critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
        high_count = sum(1 for f in findings if f.severity == "HIGH")
        med_count = sum(1 for f in findings if f.severity == "MEDIUM")
        low_count = sum(1 for f in findings if f.severity == "LOW")

        md = []
        md.append("# DO-178C DAL A Prototype Gap & Defensive Audit Report")
        md.append(f"**Target System:** `{self.icd.device_name}` ({self.icd.architecture})")
        if target_path:
            md.append(f"**Audited Code:** `{target_path}`")
        md.append(f"**Default Hardware Timeout:** `{self.icd.default_timeout_us} µs`")
        md.append("")
        md.append("## Executive Summary")
        md.append("")
        md.append("| Severity | Count | DO-178C Status |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **CRITICAL** | {critical_count} | Non-Compliant (Certification Blocker) |")
        md.append(f"| **HIGH** | {high_count} | Action Required |")
        md.append(f"| **MEDIUM** | {med_count} | Review Recommended |")
        md.append(f"| **LOW** | {low_count} | Informational |")
        md.append(f"| **TOTAL** | **{len(findings)}** | |")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## Detailed Audit Findings (DO-178C Table A-5 Compliance)")
        md.append("")

        if not findings:
            md.append("> [!NOTE]\n> Zero architectural or defensive omissions detected in audited code.")
            return "\n".join(md)

        for f in findings:
            badge = {
                "CRITICAL": "⛔ CRITICAL",
                "HIGH": "⚠️ HIGH",
                "MEDIUM": "⚠️ MEDIUM",
                "LOW": "ℹ️ LOW",
            }.get(f.severity, f.severity)

            md.append(f"### `{f.finding_id}`: {f.category} [{badge}]")
            md.append(f"- **Function:** `{f.function_name}`")
            md.append(f"- **Location:** `{f.file_path}:{f.line_number}`")
            md.append(f"- **DO-178C Objective:** {f.do178c_objective}")
            md.append(f"- **Problem:** {f.description}")
            md.append("")
            md.append("```c")
            md.append(f"// Offending code at line {f.line_number}:")
            md.append(f"{f.code_snippet}")
            md.append("```")
            md.append("")
            md.append(f"**Required Remediation:**\n> {f.remediation}")
            md.append("")
            md.append("---")
            md.append("")

        md.append("## Guidance for DO-178C DAL A Transition")
        md.append("1. **Bounded Execution:** Every loop interacting with memory-mapped I/O must have a proven deterministic upper bound.")
        md.append("2. **Hardware Register Contracts:** All status register polls must test error bitmasks before accepting data.")
        md.append("3. **Defensive Preconditions:** Public and internal API functions must validate parameter boundaries before arithmetic operations.")
        md.append("")

        return "\n".join(md)
