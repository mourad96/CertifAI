"""Prompt templates for DO-178C Defensive & Safety Gap Auditing."""

GAP_SYSTEM_PROMPT = """ROLE: Principal Avionics Safety & Certification Auditor (DO-178C Table A-5 Objectives).
TASK: Audit the provided C prototype source code against Hardware ICD constraints and DO-178C DAL A defensive programming standards.
RULES:
1. Identify all unbounded execution loops, missing loop upper bounds, and missing hardware polling timeouts.
2. Flag any unhandled hardware error registers or status bit conditions.
3. Identify missing range checks or defensive assertions on function arguments.
4. Detect potential integer and floating point overflow, underflow, or divide-by-zero risks.
5. Reference applicable DO-178C objectives (e.g. Table A-5 Objective 1: Source code complies with low-level requirements, Objective 2: Source code complies with software architecture, Objective 3: Source code is verifiable).
6. Produce an actionable, structured audit report with concrete remediation recommendations.
"""

def build_gap_audit_prompt(
    c_source_code: str,
    icd_summary: str,
    static_ast_findings: str,
) -> str:
    return f"""C Source Code under Audit:
```c
{c_source_code}
```

Hardware ICD & Register Constraints:
\"\"\"{icd_summary}\"\"\"

Pre-computed Static AST Checks:
\"\"\"{static_ast_findings}\"\"\"

Analyze this code and synthesize a comprehensive DO-178C GAP report detailing:
- Vulnerability ID / Category
- File and line location
- Severity (CRITICAL, HIGH, MEDIUM, LOW)
- DO-178C Table A-5 Objective violated
- Technical description of failure mode
- Required defensive remediation code pattern
"""
