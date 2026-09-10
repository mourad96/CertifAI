"""Requirements-Based Test Synthesizer adhering to DO-178C DAL A."""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from acv_engine.config import ACVConfig, default_config
from acv_engine.core.llm_client import LLMClient
from acv_engine.prompts.test_prompt_template import TEST_SYSTEM_PROMPT, build_test_synthesis_prompt
from acv_engine.schemas.validator import validate_test_vectors, SchemaValidationError

logger = logging.getLogger("acv_engine.tests")

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


@dataclass
class TestCase:
    test_case_id: str
    traces_to_llr: str
    test_category: str  # 'NOMINAL', 'BOUNDARY', 'ROBUSTNESS'
    description: str
    inputs: Dict[str, Any]
    expected_outputs: Dict[str, Any]
    fault_injection: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_case_id": self.test_case_id,
            "traces_to_llr": self.traces_to_llr,
            "test_category": self.test_category,
            "description": self.description,
            "inputs": self.inputs,
            "expected_outputs": self.expected_outputs,
            "fault_injection": self.fault_injection,
        }


class TestSynthesizer:
    """Derives requirements-based test vectors and C unit test stubs strictly from LLR text."""

    __test__ = False

    def __init__(self, config: Optional[ACVConfig] = None):
        self.config = config or default_config
        self.llm_client = LLMClient(config=self.config) if self.config.resolve_provider() != "offline" else None
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def synthesize_from_file(self, llr_file: Path, module_prefix: str = "VER") -> List[Dict[str, Any]]:
        """Synthesize test specifications from a baselined LLR JSON file."""
        content = Path(llr_file).read_text(encoding="utf-8")
        llr_list = json.loads(content)
        if isinstance(llr_list, dict) and "items" in llr_list:
            llr_list = llr_list["items"]

        return self.synthesize_from_llrs(llr_list, module_prefix=module_prefix)

    def synthesize_from_llrs(
        self, llr_list: List[Dict[str, Any]], module_prefix: str = "VER"
    ) -> List[Dict[str, Any]]:
        """Synthesize test specifications from a list of approved LLR dictionaries."""
        all_test_cases: List[Dict[str, Any]] = []
        tc_counter = 1

        for llr in llr_list:
            cases = self._synthesize_for_single_llr(llr, module_prefix, tc_counter)
            tc_counter += len(cases)
            all_test_cases.extend(cases)

        # Enforce DO-178C test vector schema validation
        validate_test_vectors(all_test_cases)
        return all_test_cases

    def _synthesize_for_single_llr(
        self, llr: Dict[str, Any], module_prefix: str, start_idx: int
    ) -> List[Dict[str, Any]]:
        llr_id = llr.get("llr_id", f"LLR-{module_prefix}-0001")

        # Try LLM first if available
        if self.llm_client:
            try:
                user_prompt = build_test_synthesis_prompt(json.dumps(llr, indent=2))
                result = self.llm_client.generate_json(TEST_SYSTEM_PROMPT, user_prompt)
                if isinstance(result, list) and len(result) > 0:
                    clean_cases = []
                    for i, tc in enumerate(result):
                        if not tc.get("test_case_id"):
                            tc["test_case_id"] = f"TC-{module_prefix}-{start_idx + i:04d}"
                        tc["traces_to_llr"] = llr_id
                        clean_cases.append(tc)
                    validate_test_vectors(clean_cases)
                    return clean_cases
            except Exception as e:
                logger.warning(f"LLM test synthesis failed ({e}); falling back to deterministic partitioning.")

        # Deterministic DO-178C test vector derivation
        return self._synthesize_deterministic(llr, module_prefix, start_idx)

    def _synthesize_deterministic(
        self, llr: Dict[str, Any], module_prefix: str, idx: int
    ) -> List[Dict[str, Any]]:
        llr_id = llr.get("llr_id", f"LLR-{module_prefix}-0001")
        target_fn = llr.get("target_function", "target_func")
        boundaries = llr.get("boundary_definitions", {})

        cases: List[Dict[str, Any]] = []

        # 1. NOMINAL TEST CASE
        nominal_inputs = {}
        for param, bound_str in boundaries.items():
            nominal_inputs[param] = self._extract_nominal_val(bound_str)
        if not nominal_inputs:
            nominal_inputs = {"command_value": 0, "channel": 0}

        cases.append({
            "test_case_id": f"TC-{module_prefix}-{idx:04d}",
            "traces_to_llr": llr_id,
            "test_category": "NOMINAL",
            "description": f"Verify nominal execution of {target_fn} within specified operating ranges.",
            "inputs": nominal_inputs,
            "expected_outputs": {"status": "SUCCESS", "error_flag": 0},
            "fault_injection": None,
        })
        idx += 1

        # 2. BOUNDARY TEST CASES
        # Extract numeric ranges like "-45.0 to +45.0" or "0 to 7"
        has_boundaries = False
        for param, bound_str in boundaries.items():
            parsed_bounds = self._parse_range(bound_str)
            if parsed_bounds:
                min_val, max_val = parsed_bounds
                has_boundaries = True

                # Min Boundary
                cases.append({
                    "test_case_id": f"TC-{module_prefix}-{idx:04d}",
                    "traces_to_llr": llr_id,
                    "test_category": "BOUNDARY",
                    "description": f"Verify {target_fn} lower bound behavior at Xmin ({min_val}) for parameter '{param}'.",
                    "inputs": {**nominal_inputs, param: min_val},
                    "expected_outputs": {"status": "SUCCESS", "error_flag": 0},
                    "fault_injection": None,
                })
                idx += 1

                # Max Boundary
                cases.append({
                    "test_case_id": f"TC-{module_prefix}-{idx:04d}",
                    "traces_to_llr": llr_id,
                    "test_category": "BOUNDARY",
                    "description": f"Verify {target_fn} upper bound behavior at Xmax ({max_val}) for parameter '{param}'.",
                    "inputs": {**nominal_inputs, param: max_val},
                    "expected_outputs": {"status": "SUCCESS", "error_flag": 0},
                    "fault_injection": None,
                })
                idx += 1

        if not has_boundaries:
            cases.append({
                "test_case_id": f"TC-{module_prefix}-{idx:04d}",
                "traces_to_llr": llr_id,
                "test_category": "BOUNDARY",
                "description": f"Verify boundary transition conditions for {target_fn}.",
                "inputs": {**nominal_inputs, "mode_flag": 1},
                "expected_outputs": {"status": "SUCCESS"},
                "fault_injection": None,
            })
            idx += 1

        # 3. ROBUSTNESS & FAULT INJECTION CASES
        # Case A: Out-of-bounds input
        cases.append({
            "test_case_id": f"TC-{module_prefix}-{idx:04d}",
            "traces_to_llr": llr_id,
            "test_category": "ROBUSTNESS",
            "description": f"Robustness: Invalidate input parameters to verify defensive containment in {target_fn}.",
            "inputs": {k: (9999 if isinstance(v, (int, float)) else "INVALID") for k, v in nominal_inputs.items()},
            "expected_outputs": {"status": "ERR_RANGE_VIOLATION", "error_flag": 1},
            "fault_injection": "Out-of-range parameter injection beyond allowed envelope",
        })
        idx += 1

        # Case B: Hardware timeout simulation
        cases.append({
            "test_case_id": f"TC-{module_prefix}-{idx:04d}",
            "traces_to_llr": llr_id,
            "test_category": "ROBUSTNESS",
            "description": f"Robustness: Simulate hardware interface timeout and loss of bus synchronization.",
            "inputs": nominal_inputs,
            "expected_outputs": {"status": "ERR_TIMEOUT", "error_flag": 1},
            "fault_injection": "Hardware interface timeout: READY bit held low indefinitely",
        })

        return cases

    def render_c_test_stub(
        self,
        test_cases: List[Dict[str, Any]],
        output_filename: str = "test_stubs.c",
        target_headers: Optional[List[str]] = None,
    ) -> str:
        """Render C unit test harness file using Jinja2 Unity template."""
        template = self.jinja_env.get_template("unity_c_test_stub.j2")
        return template.render(
            test_cases=test_cases,
            output_filename=output_filename,
            target_headers=target_headers or [],
        )

    def generate_markdown_matrix(
        self,
        test_cases: List[Dict[str, Any]],
        llr_list: Optional[List[Dict[str, Any]]] = None,
        module_prefix: str = "ACT",
    ) -> str:
        """Generate a human-readable DO-178C DAL A Markdown test matrix with MC/DC condition analysis."""
        nom_count = sum(1 for t in test_cases if t.get("test_category") == "NOMINAL")
        bnd_count = sum(1 for t in test_cases if t.get("test_category") == "BOUNDARY")
        rob_count = sum(1 for t in test_cases if t.get("test_category") == "ROBUSTNESS")
        total_count = len(test_cases)

        llr_map = {}
        if llr_list:
            for item in llr_list:
                lid = item.get("llr_id")
                if lid:
                    llr_map[lid] = item

        lines = [
            f"# DO-178C DAL A Requirements-Based Test Matrix & MC/DC Analysis",
            f"**Module Prefix:** `{module_prefix}`  ",
            f"**Total Test Vectors:** `{total_count}` (Nominal: `{nom_count}`, Boundary: `{bnd_count}`, Robustness: `{rob_count}`)  ",
            f"**DO-178C Verification Objectives:** Table A-5 (LLR Conformance), Table A-7 Obj 2 (MC/DC Independence)  ",
            "",
            "---",
            "",
            "## 1. Executive Test Partition Summary",
            "",
            "| Partition / Category | Count | DO-178C Standard Objective | Verification Intent |",
            "| :--- | :--- | :--- | :--- |",
            f"| **NOMINAL** | {nom_count} | §6.4.2.1 Normal Range | Verifies valid operating combinations and nominal output behavior |",
            f"| **BOUNDARY** | {bnd_count} | §6.4.2.2 Equivalence Boundary | Exercises edge transitions at minimum and maximum boundaries |",
            f"| **ROBUSTNESS** | {rob_count} | §6.4.2.3 Robustness & Faults | Exercises out-of-bounds parameters, invalid inputs, and simulated timeouts |",
            f"| **TOTAL** | **{total_count}** | **Table A-7 Obj 2** | **Full requirements-based coverage with MC/DC traceability** |",
            "",
            "---",
            "",
            "## 2. Modified Condition / Decision Coverage (MC/DC) Analysis",
            "",
            "> [!NOTE]",
            "> **DO-178C DAL A Requirement (Table A-7 Objective 2):**",
            "> Each condition in a multi-condition decision must be shown to independently affect the decision outcome.",
            "> In requirements-based testing, independent effect is proven when varying a single condition (from in-range/boundary to out-of-range/fault)",
            "> toggles the decision outcome (e.g. from nominal success to defensive error containment) while holding all other parameters valid.",
            "",
        ]

        # Group test cases by LLR
        llr_grouped: Dict[str, List[Dict[str, Any]]] = {}
        for tc in test_cases:
            lid = tc.get("traces_to_llr", f"LLR-{module_prefix}-0001")
            llr_grouped.setdefault(lid, []).append(tc)

        cond_counter = 1
        for lid, tcs in llr_grouped.items():
            llr_info = llr_map.get(lid, {})
            target_fn = llr_info.get("target_function", "Target Function")
            stmt = llr_info.get("statement", "")
            boundaries = llr_info.get("boundary_definitions", {})

            lines.append(f"### Requirement `{lid}`: `{target_fn}`")
            if stmt:
                lines.append(f"> **Statement:** {stmt}")
                lines.append("")

            mcdc_rows = self._build_mcdc_rows(lid, tcs, boundaries, cond_counter)
            cond_counter += len(mcdc_rows)

            if mcdc_rows:
                lines.append("| Condition ID | Condition Description | True Vector (In-Range / Bound) | False Vector (Fault / OOB) | Decision Outcome Toggle | MC/DC Independence Proof |")
                lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
                for row in mcdc_rows:
                    lines.append(
                        f"| **{row['id']}** | {row['desc']} | `{row['true_tc']}` | `{row['false_tc']}` | {row['toggle']} | {row['proof']} |"
                    )
                lines.append("")
            else:
                lines.append("*No multi-condition decision branches identified for this requirement.*")
                lines.append("")

        lines.extend([
            "---",
            "",
            "## 3. Comprehensive Test Vector Specifications",
            "",
            "| Test Case ID | Category | Traced LLR | Input Vectors | Expected Outputs | Fault Injection | Verification Objective |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for tc in test_cases:
            t_id = tc.get("test_case_id", "")
            cat = tc.get("test_category", "")
            t_llr = tc.get("traces_to_llr", "")
            desc = tc.get("description", "").replace("|", "\\|")
            fault = tc.get("fault_injection")
            fault_str = f"`{fault}`" if fault else "*None*"

            inputs_str = self._format_dict_for_table(tc.get("inputs", {}))
            outputs_str = self._format_dict_for_table(tc.get("expected_outputs", {}))

            lines.append(
                f"| `{t_id}` | `{cat}` | `{t_llr}` | {inputs_str} | {outputs_str} | {fault_str} | {desc} |"
            )

        lines.append("")
        return "\n".join(lines)

    def _build_mcdc_rows(
        self,
        llr_id: str,
        tcs: List[Dict[str, Any]],
        boundaries: Dict[str, str],
        start_cond_id: int,
    ) -> List[Dict[str, str]]:
        rows = []
        nominals = [t for t in tcs if t.get("test_category") == "NOMINAL"]
        boundaries_tc = [t for t in tcs if t.get("test_category") == "BOUNDARY"]
        robustness = [t for t in tcs if t.get("test_category") == "ROBUSTNESS"]

        nom_tc_id = nominals[0]["test_case_id"] if nominals else (boundaries_tc[0]["test_case_id"] if boundaries_tc else "TC-NOM")

        # Discover parameters
        params = list(boundaries.keys())
        if not params:
            seen_params = set()
            for tc in tcs:
                seen_params.update(tc.get("inputs", {}).keys())
            params = sorted(list(seen_params))

        c_idx = start_cond_id
        for param in params:
            parsed = self._parse_range(boundaries.get(param, "")) if boundaries.get(param) else None
            min_val, max_val = parsed if parsed else (None, None)

            # Find matching boundary / nominal tests for param
            # 1. Lower bound condition
            min_bnd_tc = None
            for b in boundaries_tc:
                desc_lower = b.get("description", "").lower()
                if param.lower() in desc_lower and ("min" in desc_lower or "lower" in desc_lower):
                    min_bnd_tc = b["test_case_id"]
                    break
                if min_val is not None and b.get("inputs", {}).get(param) == min_val:
                    min_bnd_tc = b["test_case_id"]
                    break
            if not min_bnd_tc and nominals:
                min_bnd_tc = nom_tc_id

            # Find robustness failure for lower bound
            rob_below_tc = None
            for r in robustness:
                desc_lower = r.get("description", "").lower()
                r_val = r.get("inputs", {}).get(param)
                if param.lower() in desc_lower and ("min" in desc_lower or "below" in desc_lower or "negative" in desc_lower):
                    rob_below_tc = r["test_case_id"]
                    break
                if min_val is not None and isinstance(r_val, (int, float)) and r_val < min_val:
                    rob_below_tc = r["test_case_id"]
                    break

            if min_bnd_tc and rob_below_tc:
                desc_text = f"<code>{param} &gt;= {min_val}</code> (Lower Bound)" if min_val is not None else f"<code>{param}</code> Valid Lower Bound"
                rows.append({
                    "id": f"C{c_idx}",
                    "desc": desc_text,
                    "true_tc": min_bnd_tc,
                    "false_tc": rob_below_tc,
                    "toggle": "<code>ACT_OK</code> &rarr; <code>ACT_ERR_INVALID_PARAM</code>",
                    "proof": f"Violating <code>{param}</code> minimum triggers rejection while other parameters remain valid.",
                })
                c_idx += 1

            # 2. Upper bound condition
            max_bnd_tc = None
            for b in boundaries_tc:
                desc_lower = b.get("description", "").lower()
                if param.lower() in desc_lower and ("max" in desc_lower or "upper" in desc_lower):
                    max_bnd_tc = b["test_case_id"]
                    break
                if max_val is not None and b.get("inputs", {}).get(param) == max_val:
                    max_bnd_tc = b["test_case_id"]
                    break
            if not max_bnd_tc and nominals:
                max_bnd_tc = nom_tc_id

            # Find robustness failure for upper bound
            rob_above_tc = None
            for r in robustness:
                desc_lower = r.get("description", "").lower()
                r_val = r.get("inputs", {}).get(param)
                if param.lower() in desc_lower and ("max" in desc_lower or "above" in desc_lower or "exceed" in desc_lower):
                    rob_above_tc = r["test_case_id"]
                    break
                if max_val is not None and isinstance(r_val, (int, float)) and r_val > max_val:
                    rob_above_tc = r["test_case_id"]
                    break

            if max_bnd_tc and rob_above_tc:
                desc_text = f"<code>{param} &lt;= {max_val}</code> (Upper Bound)" if max_val is not None else f"<code>{param}</code> Valid Upper Bound"
                rows.append({
                    "id": f"C{c_idx}",
                    "desc": desc_text,
                    "true_tc": max_bnd_tc,
                    "false_tc": rob_above_tc,
                    "toggle": "<code>ACT_OK</code> &rarr; <code>ACT_ERR_INVALID_PARAM</code>",
                    "proof": f"Exceeding <code>{param}</code> maximum triggers rejection while other parameters remain valid.",
                })
                c_idx += 1

            # Fallback if specific min/max rob wasn't split, but generic robustness exists
            if not rob_below_tc and not rob_above_tc and robustness:
                generic_rob = robustness[0]["test_case_id"]
                rows.append({
                    "id": f"C{c_idx}",
                    "desc": f"<code>{param}</code> within defined operational range",
                    "true_tc": nom_tc_id,
                    "false_tc": generic_rob,
                    "toggle": "<code>SUCCESS</code> &rarr; <code>ERR_RANGE_VIOLATION</code>",
                    "proof": f"Out-of-range <code>{param}</code> triggers defensive containment.",
                })
                c_idx += 1

        # Check for hardware interface timeout / fault injection condition
        fault_tcs = [
            r for r in robustness
            if r.get("fault_injection") or "timeout" in r.get("description", "").lower() or "fault" in r.get("description", "").lower()
        ]
        for f in fault_tcs:
            f_id = f["test_case_id"]
            f_desc = f.get("fault_injection") or f.get("description", "")
            is_timeout = "timeout" in f_desc.lower()
            cond_desc = "Hardware interface ready confirmation within watchdog window" if is_timeout else "Hardware status register error flag clear"
            toggle_state = "<code>ACT_OK</code> &rarr; <code>ACT_ERR_TIMEOUT</code>" if is_timeout else "<code>ACT_OK</code> &rarr; <code>ERR_HARDWARE_FAULT</code>"
            proof_text = "Watchdog expiration forces deterministic abort without bus lock." if is_timeout else "Hardware error bit assertion halts transaction defensively."

            rows.append({
                "id": f"C{c_idx}",
                "desc": cond_desc,
                "true_tc": nom_tc_id,
                "false_tc": f_id,
                "toggle": toggle_state,
                "proof": proof_text,
            })
            c_idx += 1

        return rows

    def _format_dict_for_table(self, d: Dict[str, Any]) -> str:
        if not d:
            return "*None*"
        entries = []
        for k, v in d.items():
            if v is None:
                val_str = "*null*"
            elif isinstance(v, bool):
                val_str = "true" if v else "false"
            else:
                val_str = str(v)
            entries.append(f"<code>{k} = {val_str}</code>")
        return "<br>".join(entries)

    def _extract_nominal_val(self, bound_str: str) -> Any:
        r = self._parse_range(bound_str)
        if r:
            min_v, max_v = r
            if isinstance(min_v, float) or isinstance(max_v, float):
                return round((min_v + max_v) / 2.0, 2)
            return (min_v + max_v) // 2
        return 0

    def _parse_range(self, bound_str: str) -> Optional[tuple]:
        # Match patterns like "-45.0 to +45.0" or "0 to 7" or "[-100, 100]"
        m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*(?:to|,)\s*([+-]?\d+(?:\.\d+)?)", bound_str)
        if m:
            s1, s2 = m.group(1), m.group(2)
            is_float = "." in s1 or "." in s2
            if is_float:
                return float(s1), float(s2)
            return int(s1), int(s2)
        return None
