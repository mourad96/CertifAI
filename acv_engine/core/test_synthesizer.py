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
