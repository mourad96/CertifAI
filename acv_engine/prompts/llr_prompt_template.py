"""Prompt templates for Candidate LLR Synthesis."""

LLR_SYSTEM_PROMPT = """ROLE: Senior Avionics Systems & Certification Engineer (DO-178C DAL A).
TASK: Analyze the provided C AST/Source and allocated High-Level Requirement (HLR).
RULES:
1. NEVER describe source code mechanics (e.g., "increments a counter", "loops over buffer", "calls function X").
2. ALWAYS describe inputs, transformations, bounds, outputs, and failure modes.
3. Every requirement must use unambiguous terminology ("shall") and identify clear pass/fail criteria.
4. If the code implements behavior not covered by the parent HLR, mark derived_requirement = true and provide a safety rationale.
5. If the code has no matching parent HLR, set parent_hlr_ref to "DERIVED" or "NONE", derived_requirement = true, and explain the safety rationale.
6. The output must strictly adhere to the CandidateLLRList JSON schema format.
7. Return ONLY valid JSON array with objects matching:
   - llr_id: "LLR-<MODULE>-<4_DIGIT_NUM>" (e.g., "LLR-ACT-0001")
   - parent_hlr_ref: "HLR-XXX-NNN" or "DERIVED"
   - target_function: function name
   - pre_conditions: array of string conditions
   - statement: "The software shall ..."
   - post_conditions: array of string conditions
   - boundary_definitions: key-value dictionary of bounds (e.g., {"command_deg": "-45.0 to +45.0 deg", "timeout_us": "<= 500 us"})
   - derived_requirement: true | false
   - rationale: safety and functional rationale
"""

def build_llr_synthesis_prompt(
    function_name: str,
    function_signature: str,
    function_source: str,
    parent_hlr_id: str,
    parent_hlr_desc: str,
    safety_impact: str,
    boundary_hints: str = "",
) -> str:
    return f"""Target Function: {function_name}
Signature: {function_signature}
Allocated Parent HLR ID: {parent_hlr_id}
HLR Safety Impact: {safety_impact}
Parent HLR Description:
\"\"\"{parent_hlr_desc}\"\"\"

Function Source Code:
```c
{function_source}
```

Additional Boundary / Interface Hints:
{boundary_hints if boundary_hints else "None"}

Synthesize candidate Low-Level Requirements (LLRs) for this function. Ensure strict DO-178C DAL A compliance, contractual formulation, and valid JSON output.
"""
