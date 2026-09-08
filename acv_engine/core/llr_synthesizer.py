"""Candidate Low-Level Requirements (LLR) Synthesizer adhering to DO-178C DAL A."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from acv_engine.config import ACVConfig, default_config
from acv_engine.core.llm_client import LLMClient
from acv_engine.parsers.c_ast_parser import CASTParser, FunctionInfo, ParsedCFile
from acv_engine.parsers.hlr_parser import HLRDocument, HLRItem, HLRParser
from acv_engine.prompts.llr_prompt_template import LLR_SYSTEM_PROMPT, build_llr_synthesis_prompt
from acv_engine.schemas.validator import validate_llr, SchemaValidationError

logger = logging.getLogger("acv_engine.llr")


@dataclass
class CandidateLLR:
    llr_id: str
    parent_hlr_ref: str
    target_function: str
    pre_conditions: List[str]
    statement: str
    post_conditions: List[str]
    boundary_definitions: Dict[str, str]
    derived_requirement: bool
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "llr_id": self.llr_id,
            "parent_hlr_ref": self.parent_hlr_ref,
            "target_function": self.target_function,
            "pre_conditions": self.pre_conditions,
            "statement": self.statement,
            "post_conditions": self.post_conditions,
            "boundary_definitions": self.boundary_definitions,
            "derived_requirement": self.derived_requirement,
            "rationale": self.rationale,
        }


class LLRSynthesizer:
    """Synthesizes formal DO-178C Candidate LLRs from C AST and Allocated HLRs."""

    def __init__(self, hlr_doc: HLRDocument, config: Optional[ACVConfig] = None):
        self.hlr_doc = hlr_doc
        self.config = config or default_config
        self.ast_parser = CASTParser()
        self.llm_client = LLMClient(config=self.config) if self.config.resolve_provider() != "offline" else None

    def synthesize_from_file(
        self, c_path: Path, header_path: Optional[Path] = None, module_prefix: str = "REQ"
    ) -> List[Dict[str, Any]]:
        """Synthesize candidate LLRs for all functions in the provided C source file."""
        parsed_c = self.ast_parser.parse_file(c_path)
        header_text = ""
        if header_path and header_path.exists():
            header_text = header_path.read_text(encoding="utf-8")

        candidates: List[Dict[str, Any]] = []
        llr_index = 1

        for fn in parsed_c.functions:
            # Map function to parent HLR candidate
            matched_hlr = self.hlr_doc.match_function(fn.name, fn.body_source)
            fn_candidates = self._synthesize_function_llrs(
                fn, matched_hlr, header_text, module_prefix, llr_index
            )
            llr_index += len(fn_candidates)
            candidates.extend(fn_candidates)

        # Enforce DO-178C schema validation
        validate_llr(candidates)
        return candidates

    def _synthesize_function_llrs(
        self,
        fn: FunctionInfo,
        matched_hlr: Optional[HLRItem],
        header_text: str,
        module_prefix: str,
        start_idx: int,
    ) -> List[Dict[str, Any]]:
        # If LLM is available and active, attempt LLM synthesis first
        if self.llm_client:
            try:
                hlr_id = matched_hlr.hlr_id if matched_hlr else "NONE"
                hlr_desc = matched_hlr.description if matched_hlr else "No parent HLR allocated for this prototype function."
                safety_impact = matched_hlr.safety_impact if matched_hlr else "NO_SAFETY"
                sig = f"{fn.return_type} {fn.name}({', '.join(f'{p.type_name} {p.name}' for p in fn.parameters)})"

                user_prompt = build_llr_synthesis_prompt(
                    function_name=fn.name,
                    function_signature=sig,
                    function_source=fn.body_source,
                    parent_hlr_id=hlr_id,
                    parent_hlr_desc=hlr_desc,
                    safety_impact=safety_impact,
                    boundary_hints=header_text[:400] if header_text else "",
                )

                result = self.llm_client.generate_json(LLR_SYSTEM_PROMPT, user_prompt)
                if isinstance(result, list) and len(result) > 0:
                    # Verify each item format
                    clean_items = []
                    for i, item in enumerate(result):
                        if not item.get("llr_id"):
                            item["llr_id"] = f"LLR-{module_prefix}-{start_idx + i:04d}"
                        if matched_hlr and not item.get("parent_hlr_ref"):
                            item["parent_hlr_ref"] = matched_hlr.hlr_id
                        elif not matched_hlr:
                            item["parent_hlr_ref"] = "DERIVED"
                            item["derived_requirement"] = True
                            if not item.get("rationale"):
                                item["rationale"] = f"Unallocated prototype functionality in {fn.name}; classified as derived requirement."
                        clean_items.append(item)
                    validate_llr(clean_items)
                    return clean_items
            except Exception as e:
                logger.warning(f"LLM synthesis failed or unavailable ({e}); falling back to deterministic synthesis engine.")

        # Deterministic DO-178C contractual synthesis engine
        return self._synthesize_function_deterministic(fn, matched_hlr, module_prefix, start_idx)

    def _synthesize_function_deterministic(
        self,
        fn: FunctionInfo,
        matched_hlr: Optional[HLRItem],
        module_prefix: str,
        idx: int,
    ) -> List[Dict[str, Any]]:
        """Deterministic contract-driven synthesizer enforcing DO-178C syntax and avoiding procedural prose."""
        llr_id = f"LLR-{module_prefix}-{idx:04d}"
        is_derived = matched_hlr is None
        parent_hlr_ref = matched_hlr.hlr_id if matched_hlr else "DERIVED"

        # Formulate pre-conditions
        pre_conditions = []
        boundaries = {}
        for p in fn.parameters:
            pre_conditions.append(f"Input parameter '{p.name}' shall be valid and within architectural range.")
            if "angle" in p.name.lower() or "deg" in p.name.lower():
                boundaries[p.name] = "-45.0 to +45.0 deg"
            elif "rate" in p.name.lower():
                boundaries[p.name] = "-100.0 to +100.0 deg/s"
            elif "id" in p.name.lower() or "ch" in p.name.lower():
                boundaries[p.name] = "0 to 7"
            elif "len" in p.name.lower() or "count" in p.name.lower():
                boundaries[p.name] = "1 to 256"
            else:
                boundaries[p.name] = f"Valid range for type {p.type_name}"

        # Formulate contractual statement
        if matched_hlr:
            fn_readable = fn.name.replace("_", " ")
            statement = (
                f"The software shall execute {fn_readable} to satisfy {matched_hlr.hlr_id} "
                f"by processing input values within defined operating tolerances and outputting "
                f"contractual state updates without unbounded delay."
            )
            rationale = (
                f"Directly traces to parent requirement {matched_hlr.hlr_id} "
                f"({matched_hlr.safety_impact} safety category) for verified function {fn.name}."
            )
        else:
            statement = (
                f"The software shall provide internal defensive utility {fn.name} "
                f"to support subsystem execution while strictly bounding resource usage."
            )
            rationale = (
                f"CANDIDATE_DERIVED_REQUIREMENT: Function '{fn.name}' has no allocated parent HLR. "
                "Classified as derived functionality requiring systems engineer review and safety validation."
            )

        # Formulate post-conditions
        post_conditions = []
        if fn.return_type and fn.return_type != "void":
            post_conditions.append(f"Function shall return status code or evaluated value conforming to {fn.return_type}.")
        else:
            post_conditions.append("Function shall complete without unhandled exception or arithmetic fault.")

        candidate = {
            "llr_id": llr_id,
            "parent_hlr_ref": parent_hlr_ref,
            "target_function": fn.name,
            "pre_conditions": pre_conditions if pre_conditions else ["System initialized in operational mode."],
            "statement": statement,
            "post_conditions": post_conditions,
            "boundary_definitions": boundaries if boundaries else {"execution_state": "NOMINAL"},
            "derived_requirement": is_derived,
            "rationale": rationale,
        }

        return [candidate]
