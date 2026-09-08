"""Hardware Interface Control Document (ICD) Parser and Indexer."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import yaml

from acv_engine.schemas.validator import validate_icd


@dataclass
class BitfieldInfo:
    mask: str
    description: str


@dataclass
class RegisterDefinition:
    name: str
    address: str = "0x0"
    description: str = ""
    access: str = "RW"
    ready_mask: Optional[str] = None
    error_mask: Optional[str] = None
    reset_value: Optional[str] = None
    timeout_us: Optional[float] = None
    bitfields: Dict[str, BitfieldInfo] = field(default_factory=dict)


@dataclass
class BusDefinition:
    name: str
    bus_type: str = ""
    max_frequency_hz: Optional[float] = None


@dataclass
class ICDDocument:
    device_name: str
    architecture: str = "Generic"
    clock_freq_hz: Optional[float] = None
    default_timeout_us: float = 1000.0
    registers: List[RegisterDefinition] = field(default_factory=list)
    buses: List[BusDefinition] = field(default_factory=list)
    registers_by_name: Dict[str, RegisterDefinition] = field(default_factory=dict)

    def __post_init__(self):
        if not self.registers_by_name:
            self.registers_by_name = {r.name: r for r in self.registers}

    def get_register(self, name: str) -> Optional[RegisterDefinition]:
        return self.registers_by_name.get(name)

    def get_register_names(self) -> Set[str]:
        return set(self.registers_by_name.keys())


class ICDParser:
    """Parses and validates Hardware ICD constraints."""

    @classmethod
    def parse_file(cls, file_path: Path) -> ICDDocument:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"ICD file does not exist: {p}")

        content = p.read_text(encoding="utf-8")
        if p.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)

        return cls.parse_data(data)

    @classmethod
    def parse_data(cls, data: Any) -> ICDDocument:
        validate_icd(data)

        regs = []
        for r in data.get("registers", []):
            bitfields = {}
            for bf_name, bf_val in r.get("bitfields", {}).items():
                bitfields[bf_name] = BitfieldInfo(
                    mask=str(bf_val.get("mask", "")),
                    description=bf_val.get("description", ""),
                )
            regs.append(
                RegisterDefinition(
                    name=r["name"],
                    address=str(r.get("address", "0x0")),
                    description=r.get("description", ""),
                    access=r.get("access", "RW"),
                    ready_mask=str(r["ready_mask"]) if r.get("ready_mask") is not None else None,
                    error_mask=str(r["error_mask"]) if r.get("error_mask") is not None else None,
                    reset_value=str(r["reset_value"]) if r.get("reset_value") is not None else None,
                    timeout_us=float(r["timeout_us"]) if r.get("timeout_us") is not None else None,
                    bitfields=bitfields,
                )
            )

        buses = []
        for b in data.get("buses", []):
            buses.append(
                BusDefinition(
                    name=b["name"],
                    bus_type=b.get("type", ""),
                    max_frequency_hz=float(b["max_frequency_hz"]) if b.get("max_frequency_hz") is not None else None,
                )
            )

        return ICDDocument(
            device_name=data["device_name"],
            architecture=data.get("architecture", "Generic"),
            clock_freq_hz=float(data["clock_freq_hz"]) if data.get("clock_freq_hz") is not None else None,
            default_timeout_us=float(data.get("default_timeout_us", 1000.0)),
            registers=regs,
            buses=buses,
        )
