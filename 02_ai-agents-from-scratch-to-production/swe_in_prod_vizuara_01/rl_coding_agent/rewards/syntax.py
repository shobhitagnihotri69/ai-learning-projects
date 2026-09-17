"""Syntax validation reward for Python coding agents using AST parsing."""

import ast
from typing import Dict, Tuple


class SyntaxReward:
    """Evaluates whether changed or generated Python files are syntactically valid."""

    def __init__(self, valid_reward: float = 0.2, invalid_penalty: float = -0.5):
        self.valid_reward = valid_reward
        self.invalid_penalty = invalid_penalty

    def evaluate_code(self, code_str: str) -> Tuple[float, str]:
        """Parse Python code string with ast.parse.
        
        Returns:
            (reward, message)
        """
        if not code_str.strip():
            return 0.0, "Empty code"
        try:
            ast.parse(code_str)
            return self.valid_reward, "Valid Python syntax"
        except SyntaxError as e:
            return self.invalid_penalty, f"SyntaxError at line {e.lineno}: {e.msg}"

    def evaluate_files(self, files: Dict[str, str]) -> Tuple[float, Dict[str, str]]:
        """Evaluate syntax of multiple files.
        
        Returns:
            (total_reward, details_dict)
        """
        py_files = {k: v for k, v in files.items() if k.endswith(".py")}
        if not py_files:
            return 0.0, {}

        total_reward = 0.0
        details = {}
        for fname, content in py_files.items():
            r, msg = self.evaluate_code(content)
            total_reward += r
            details[fname] = msg

        # Normalize score
        avg_reward = total_reward / len(py_files)
        return round(avg_reward, 3), details
