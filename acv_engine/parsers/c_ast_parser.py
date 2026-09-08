"""C AST Parser using Tree-Sitter for DO-178C static inspection."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import tree_sitter_c as tsc
from tree_sitter import Language, Node, Parser


@dataclass
class ParameterInfo:
    name: str
    type_name: str


@dataclass
class LoopInfo:
    loop_type: str  # 'while', 'for', 'do_while'
    condition_text: str
    body_text: str
    start_line: int
    end_line: int
    is_empty_body: bool
    has_timeout_or_break: bool
    polls_hardware: bool
    hardware_registers_polled: List[str] = field(default_factory=list)


@dataclass
class RegisterAccessInfo:
    register_name: str
    access_type: str  # 'READ', 'WRITE', 'POLL'
    line_number: int
    expression_text: str


@dataclass
class ArithmeticOpInfo:
    operator: str
    expression_text: str
    line_number: int
    operands: List[str] = field(default_factory=list)
    risk_type: str = "OVERFLOW"  # 'OVERFLOW', 'DIV_ZERO', 'FLOAT_PRECISION'


@dataclass
class FunctionInfo:
    name: str
    return_type: str
    parameters: List[ParameterInfo]
    body_source: str
    start_line: int
    end_line: int
    file_path: str
    loops: List[LoopInfo] = field(default_factory=list)
    register_accesses: List[RegisterAccessInfo] = field(default_factory=list)
    called_functions: List[str] = field(default_factory=list)
    checked_parameters: List[str] = field(default_factory=list)
    error_checks: List[str] = field(default_factory=list)
    arithmetic_ops: List[ArithmeticOpInfo] = field(default_factory=list)
    returns: List[str] = field(default_factory=list)
    switches_missing_default: List[int] = field(default_factory=list)


@dataclass
class ParsedCFile:
    file_path: str
    functions: List[FunctionInfo] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    macros: List[str] = field(default_factory=list)
    raw_source: str = ""


class CASTParser:
    """Extracts functions, loops, register accesses, and safety invariants from C code."""

    def __init__(self, known_registers: Optional[Set[str]] = None):
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)
        self.known_registers = set(known_registers or [])

    def add_known_registers(self, registers: Set[str]) -> None:
        self.known_registers.update(registers)

    def parse_file(self, file_path: Path) -> ParsedCFile:
        """Parse a single C source or header file."""
        path_str = str(file_path)
        with open(file_path, "rb") as f:
            source_bytes = f.read()
        return self.parse_bytes(source_bytes, file_path=path_str)

    def parse_directory(self, dir_path: Path) -> List[ParsedCFile]:
        """Parse all .c and .h files recursively in a directory."""
        results = []
        extensions = [".c", ".h", ".s"]
        for ext in extensions:
            for p in sorted(dir_path.rglob(f"*{ext}")):
                if p.is_file():
                    results.append(self.parse_file(p))
        return results

    def parse_bytes(self, source_bytes: bytes, file_path: str = "") -> ParsedCFile:
        """Parse raw C source code bytes."""
        tree = self.parser.parse(source_bytes)
        source_text = source_bytes.decode("utf-8", errors="replace")
        parsed = ParsedCFile(file_path=file_path, raw_source=source_text)

        root = tree.root_node
        self._extract_top_level(root, source_bytes, parsed)
        return parsed

    def _extract_top_level(self, root: Node, source_bytes: bytes, parsed: ParsedCFile) -> None:
        for child in root.children:
            if child.type == "function_definition":
                fn = self._parse_function_definition(child, source_bytes, parsed.file_path)
                if fn:
                    parsed.functions.append(fn)
            elif child.type == "preproc_include":
                parsed.includes.append(self._node_text(child, source_bytes).strip())
            elif child.type == "preproc_def":
                parsed.macros.append(self._node_text(child, source_bytes).strip())

    def _node_text(self, node: Node, source_bytes: bytes) -> str:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _parse_function_definition(
        self, node: Node, source_bytes: bytes, file_path: str
    ) -> Optional[FunctionInfo]:
        # Extract return type
        return_type = "void"
        type_node = node.child_by_field_name("type")
        if type_node:
            return_type = self._node_text(type_node, source_bytes).strip()

        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return None

        fn_name, parameters = self._parse_declarator(declarator, source_bytes)
        if not fn_name:
            return None

        body_node = node.child_by_field_name("body")
        body_text = self._node_text(body_node, source_bytes) if body_node else ""
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1

        fn_info = FunctionInfo(
            name=fn_name,
            return_type=return_type,
            parameters=parameters,
            body_source=body_text,
            start_line=start_line,
            end_line=end_line,
            file_path=file_path,
        )

        if body_node:
            self._inspect_body(body_node, source_bytes, fn_info)

        return fn_info

    def _parse_declarator(
        self, declarator: Node, source_bytes: bytes
    ) -> (str, List[ParameterInfo]):
        # Declarator might be nested inside pointer_declarator or function_declarator
        curr = declarator
        while curr and curr.type == "pointer_declarator":
            curr = curr.child_by_field_name("declarator")

        if not curr or curr.type != "function_declarator":
            # If direct identifier
            if curr and curr.type == "identifier":
                return self._node_text(curr, source_bytes).strip(), []
            return "", []

        name_node = curr.child_by_field_name("declarator")
        while name_node and name_node.type == "pointer_declarator":
            name_node = name_node.child_by_field_name("declarator")

        name = self._node_text(name_node, source_bytes).strip() if name_node else ""

        parameters: List[ParameterInfo] = []
        param_list_node = curr.child_by_field_name("parameters")
        if param_list_node:
            for child in param_list_node.children:
                if child.type == "parameter_declaration":
                    p_type_node = child.child_by_field_name("type")
                    p_decl_node = child.child_by_field_name("declarator")
                    p_type = self._node_text(p_type_node, source_bytes).strip() if p_type_node else "void"
                    p_name = self._node_text(p_decl_node, source_bytes).strip() if p_decl_node else ""
                    # Handle pointer syntax in declarator
                    if p_name.startswith("*"):
                        p_name = p_name.lstrip("*").strip()
                        p_type += "*"
                    if p_name:
                        parameters.append(ParameterInfo(name=p_name, type_name=p_type))

        return name, parameters

    def _inspect_body(self, body_node: Node, source_bytes: bytes, fn_info: FunctionInfo) -> None:
        param_names = {p.name for p in fn_info.parameters}

        def walk(n: Node):
            # Inspect loops
            if n.type in ("while_statement", "for_statement", "do_statement"):
                loop_info = self._analyze_loop(n, source_bytes)
                fn_info.loops.append(loop_info)

            # Inspect calls
            elif n.type == "call_expression":
                fn_call_node = n.child_by_field_name("function")
                if fn_call_node:
                    called_name = self._node_text(fn_call_node, source_bytes).strip()
                    fn_info.called_functions.append(called_name)

            # Inspect returns
            elif n.type == "return_statement":
                fn_info.returns.append(self._node_text(n, source_bytes).strip())

            # Inspect input parameter checks
            elif n.type == "if_statement":
                cond = n.child_by_field_name("condition")
                if cond:
                    cond_text = self._node_text(cond, source_bytes)
                    for p in param_names:
                        if p in cond_text:
                            fn_info.checked_parameters.append(p)
                    # Check for error handling in condition
                    if any(kw in cond_text.upper() for kw in ["ERR", "FAULT", "FAIL", "STATUS"]):
                        fn_info.error_checks.append(cond_text)

            # Inspect switch default
            elif n.type == "switch_statement":
                has_default = any(
                    child.type == "default_statement" or
                    (child.type == "case_statement" and "default" in self._node_text(child, source_bytes))
                    for child in n.children
                )
                if not has_default:
                    # Look inside body compound statement if present
                    switch_body = n.child_by_field_name("body")
                    if switch_body:
                        has_default = any(
                            c.type == "default_statement" or
                            "default:" in self._node_text(c, source_bytes)
                            for c in switch_body.children
                        )
                if not has_default:
                    fn_info.switches_missing_default.append(n.start_point[0] + 1)

            # Inspect arithmetic risks
            elif n.type == "binary_expression":
                op_node = n.children[1] if len(n.children) > 1 else None
                if op_node:
                    op_str = self._node_text(op_node, source_bytes).strip()
                    if op_str in ("/", "%"):
                        fn_info.arithmetic_ops.append(
                            ArithmeticOpInfo(
                                operator=op_str,
                                expression_text=self._node_text(n, source_bytes).strip(),
                                line_number=n.start_point[0] + 1,
                                risk_type="DIV_ZERO",
                            )
                        )
                    elif op_str in ("*", "+", "<<"):
                        fn_info.arithmetic_ops.append(
                            ArithmeticOpInfo(
                                operator=op_str,
                                expression_text=self._node_text(n, source_bytes).strip(),
                                line_number=n.start_point[0] + 1,
                                risk_type="OVERFLOW",
                            )
                        )

            # Inspect register access
            self._inspect_register_access(n, source_bytes, fn_info)

            # Recurse children
            for child in n.children:
                walk(child)

        walk(body_node)

    def _analyze_loop(self, loop_node: Node, source_bytes: bytes) -> LoopInfo:
        loop_type = (
            "while" if loop_node.type == "while_statement"
            else "for" if loop_node.type == "for_statement"
            else "do_while"
        )
        cond_node = (
            loop_node.child_by_field_name("condition")
            if loop_type != "for"
            else loop_node.child_by_field_name("condition")
        )
        cond_text = self._node_text(cond_node, source_bytes).strip() if cond_node else ""

        body_node = loop_node.child_by_field_name("body")
        body_text = self._node_text(body_node, source_bytes).strip() if body_node else ""

        is_empty_body = body_text in ("", ";", "{}")

        # Check for timeout / break counter in loop
        has_timeout_or_break = False
        if "break;" in body_text or "return " in body_text:
            has_timeout_or_break = True
        if any(t in body_text.lower() for t in ["timeout", "count", "retries", "limit"]):
            has_timeout_or_break = True

        # Check if condition polls hardware
        polls_hardware = False
        polled_regs = []
        for reg in self.known_registers:
            if reg in cond_text or reg in body_text:
                polls_hardware = True
                polled_regs.append(reg)

        # Also generic hardware polling pattern: bitwise & with status / volatile / REG
        if any(w in cond_text.upper() for w in ["REG", "STATUS", "READY", "BUSY", "FLAG", "0X"]):
            if "&" in cond_text or "==" in cond_text or "!=" in cond_text:
                polls_hardware = True

        return LoopInfo(
            loop_type=loop_type,
            condition_text=cond_text,
            body_text=body_text,
            start_line=loop_node.start_point[0] + 1,
            end_line=loop_node.end_point[0] + 1,
            is_empty_body=is_empty_body,
            has_timeout_or_break=has_timeout_or_break,
            polls_hardware=polls_hardware,
            hardware_registers_polled=polled_regs,
        )

    def _inspect_register_access(
        self, node: Node, source_bytes: bytes, fn_info: FunctionInfo
    ) -> None:
        # Detect identifiers matching known registers or patterns like REG_*, *_REG, HW_*
        if node.type == "identifier":
            text = self._node_text(node, source_bytes).strip()
            is_reg = (
                text in self.known_registers or
                text.endswith("_REG") or
                text.startswith("REG_") or
                text.startswith("HW_")
            )
            if is_reg:
                # Check parent to determine read or write
                parent = node.parent
                access = "READ"
                if parent and parent.type == "assignment_expression":
                    left = parent.child_by_field_name("left")
                    if left and node in (left, left.children):
                        access = "WRITE"
                expr_text = self._node_text(parent, source_bytes).strip() if parent else text
                fn_info.register_accesses.append(
                    RegisterAccessInfo(
                        register_name=text,
                        access_type=access,
                        line_number=node.start_point[0] + 1,
                        expression_text=expr_text,
                    )
                )
