"""High-Level Requirements (HLR) Parser and Indexer."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from acv_engine.schemas.validator import validate_hlr, SchemaValidationError


@dataclass
class HLRItem:
    hlr_id: str
    description: str
    safety_impact: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class HLRDocument:
    items: List[HLRItem]
    by_id: Dict[str, HLRItem] = field(default_factory=dict)

    def __post_init__(self):
        if not self.by_id:
            self.by_id = {item.hlr_id: item for item in self.items}

    def get_by_id(self, hlr_id: str) -> Optional[HLRItem]:
        return self.by_id.get(hlr_id)

    def match_function(self, fn_name: str, fn_body: str = "", interface_hint: str = "") -> Optional[HLRItem]:
        """Match function to candidate HLR based on interface names and specific semantic keywords."""
        fn_clean = fn_name.lower().strip()
        fn_tokens = set(fn_clean.replace("_", " ").split())
        # Filter out common avionics prefixes and generic terms
        stop_words = {"actuator", "control", "module", "system", "software", "flight", "data", "device", "the", "shall"}
        meaningful_tokens = {tok for tok in fn_tokens if len(tok) > 3 and tok not in stop_words}

        best_match: Optional[HLRItem] = None
        best_score = 0

        for item in self.items:
            score = 0
            desc_lower = item.description.lower()
            ifaces_lower = [iface.lower() for iface in item.interfaces]

            # Direct interface matching has highest priority
            if any(fn_clean == iface for iface in ifaces_lower):
                score += 20
            elif any(fn_clean in iface or iface in fn_clean for iface in ifaces_lower if len(iface) > 5):
                score += 10
            elif any(iface in fn_body.lower() for iface in ifaces_lower if len(iface) > 5):
                score += 5

            # Meaningful function token matching in description
            for tok in meaningful_tokens:
                if tok in desc_lower:
                    score += 3

            # Interface hint
            if interface_hint and any(interface_hint.lower() in iface for iface in ifaces_lower):
                score += 4

            if score > best_score:
                best_score = score
                best_match = item

        # Require a threshold of at least 6 to declare a legitimate match
        return best_match if best_score >= 6 else None


class HLRParser:
    """Parses and validates High-Level Requirements."""

    @classmethod
    def parse_file(cls, file_path: Path) -> HLRDocument:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"HLR file does not exist: {p}")

        content = p.read_text(encoding="utf-8")
        if p.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)

        return cls.parse_data(data)

    @classmethod
    def parse_data(cls, data: Any) -> HLRDocument:
        # Validate schema
        validate_hlr(data)

        items = []
        for raw in data:
            items.append(
                HLRItem(
                    hlr_id=raw["hlr_id"],
                    description=raw["description"],
                    safety_impact=raw["safety_impact"],
                    interfaces=raw.get("interfaces", []),
                )
            )
        return HLRDocument(items=items)
