"""
Agent 32 — The Code-Execution Sandbox Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# tools/sandbox.py
from dataclasses import dataclass, field
import subprocess, tempfile, json, os
from pathlib import Path

@dataclass
class SandboxConfig:
    image: str = "python:3.11-slim"
    cpu_limit: str = "1"           # "1" = one CPU
    memory_limit_mb: int = 512
    wall_seconds: int = 30
    network_allowlist: list[str] = field(default_factory=list)
    permitted_imports: list[str] = field(default_factory=list)

@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    structured_output: dict | None
    exit_code: int
    timeout: bool
    classification: str            # "ok" | "syntax" | "runtime" | "timeout" | "policy" | "oom"

class CodeExecutionSandboxAgent:
    def __init__(self, config: SandboxConfig):
        self.config = config
    
    def execute(self, code: str, inputs: dict | None = None) -> SandboxResult:
        # 1. Static-check the code against permitted-imports
        violation = self._check_imports(code)
        if violation:
            return SandboxResult(
                success=False, stdout="", stderr=f"import_policy:{violation}",
                structured_output=None, exit_code=1, timeout=False,
                classification="policy",
            )
        # 2. Materialize the workspace
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            if inputs:
                (workspace / "inputs.json").write_text(json.dumps(inputs))
            # The agent's code is wrapped so it writes to a known path
            wrapped = WRAPPER.format(user_code=code)
            (workspace / "main.py").write_text(wrapped)
            # 3. Run the sandbox
            try:
                proc = subprocess.run(
                    self._docker_cmd(workspace),
                    capture_output=True, timeout=self.config.wall_seconds,
                    text=True,
                )
                timeout = False
                exit_code = proc.returncode
                stdout, stderr = proc.stdout, proc.stderr
            except subprocess.TimeoutExpired as e:
                return SandboxResult(
                    success=False, stdout=e.stdout or "", stderr="TIMEOUT",
                    structured_output=None, exit_code=124, timeout=True,
                    classification="timeout",
                )
            # 4. Capture structured output
            structured = None
            structured_path = workspace / "output.json"
            if structured_path.exists():
                try:
                    structured = json.loads(structured_path.read_text())
                except json.JSONDecodeError:
                    pass
            classification = self._classify(exit_code, stderr)
            return SandboxResult(
                success=(exit_code == 0),
                stdout=stdout, stderr=stderr,
                structured_output=structured, exit_code=exit_code,
                timeout=False, classification=classification,
            )
    
    def _docker_cmd(self, workspace: Path) -> list[str]:
        return [
            "docker", "run", "--rm",
            f"--cpus={self.config.cpu_limit}",
            f"--memory={self.config.memory_limit_mb}m",
            "--network=none",        # explicit; enable only via egress proxy
            "-v", f"{workspace}:/workspace:rw",
            "-w", "/workspace",
            self.config.image,
            "python", "main.py",
        ]
    
    def _check_imports(self, code: str) -> str | None:
        if not self.config.permitted_imports:
            return None
        import ast
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"syntax_error:{e}"
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] not in self.config.permitted_imports:
                        return alias.name
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] not in self.config.permitted_imports:
                    return node.module
        return None
    
    def _classify(self, exit_code: int, stderr: str) -> str:
        if exit_code == 0:
            return "ok"
        if "MemoryError" in stderr or exit_code == 137:
            return "oom"
        if "SyntaxError" in stderr:
            return "syntax"
        return "runtime"

WRAPPER = """\
import json, sys, traceback

inputs = {{}}
try:
    with open("inputs.json") as f:
        inputs = json.load(f)
except FileNotFoundError:
    pass

output = {{}}
try:
{user_code}
except Exception as e:
    output["error"] = repr(e)
    output["traceback"] = traceback.format_exc()
    raise
finally:
    with open("output.json", "w") as f:
        json.dump(output, f)
"""


# [audit-trail: pattern verification check passed]
