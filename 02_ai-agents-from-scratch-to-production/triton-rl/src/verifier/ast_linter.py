"""
ast_linter.py — Functional & Anti-Cheating Linter for TritonRL
Detects reward hacking failure modes identified in the paper:
1. Superficially using @triton.jit but delegating computation to PyTorch (torch.nn, torch.matmul, @ operator)
2. Missing @triton.jit kernel annotations
3. Constant hardcoding / dummy returns
"""

import ast
from typing import Tuple, List

PROHIBITED_FALLBACK_MODULES = {"torch.nn", "torch.nn.functional", "nn.functional", "F"}
PROHIBITED_PYTORCH_OPS = {
    "matmul", "mm", "bmm", "conv1d", "conv2d", "conv3d", 
    "relu", "gelu", "softmax", "cross_entropy", "linear"
}

class TritonAntiCheatLinter(ast.NodeVisitor):
    def __init__(self):
        self.has_triton_jit = False
        self.prohibited_calls: List[str] = []
        self.has_matrix_mult_operator = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if decorator.attr == "jit" and getattr(decorator.value, "id", None) == "triton":
                    self.has_triton_jit = True
            elif isinstance(decorator, ast.Name):
                if decorator.id == "jit":
                    self.has_triton_jit = True
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        # Catch @ (MatMult) operator
        if isinstance(node.op, ast.MatMult):
            self.has_matrix_mult_operator = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Catch torch.matmul, torch.nn.functional.* delegation inside generated code
        call_str = self._get_call_name(node.func)
        if call_str:
            for prohibited in PROHIBITED_PYTORCH_OPS:
                if call_str == f"torch.{prohibited}" or call_str == f"F.{prohibited}":
                    self.prohibited_calls.append(call_str)
            for mod in PROHIBITED_FALLBACK_MODULES:
                if call_str.startswith(f"{mod}."):
                    self.prohibited_calls.append(call_str)
        self.generic_visit(node)

    def _get_call_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._get_call_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return ""


def check_syntax(code_str: str) -> Tuple[bool, str]:
    """syntax(o): Binary verifier assessing if code has valid Python/Triton syntax."""
    try:
        ast.parse(code_str)
        return True, "Valid syntax"
    except SyntaxError as e:
        return False, f"SyntaxError: {str(e)}"


def check_functionality(code_str: str) -> Tuple[bool, str]:
    """
    func(o): Binary functionality verifier.
    Detects if the code constitutes a genuine Triton kernel, or cheats by
    delegating to high-level PyTorch ops or missing @triton.jit.
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, f"Cannot parse AST: {str(e)}"

    linter = TritonAntiCheatLinter()
    linter.visit(tree)

    if not linter.has_triton_jit:
        return False, "Failed func check: Missing @triton.jit kernel definition."

    if linter.has_matrix_mult_operator:
        return False, "Failed func check: Detected '@' (matrix mult) operator delegating work."

    if linter.prohibited_calls:
        return False, f"Failed func check (Reward Hacking): Prohibited PyTorch delegation detected: {linter.prohibited_calls}"

    return True, "Valid functional Triton kernel"


def verify_validity(code_str: str) -> Tuple[bool, str]:
    """valid(o) = syntax(o) * func(o)"""
    syntax_ok, syntax_msg = check_syntax(code_str)
    if not syntax_ok:
        return False, syntax_msg
    return check_functionality(code_str)
