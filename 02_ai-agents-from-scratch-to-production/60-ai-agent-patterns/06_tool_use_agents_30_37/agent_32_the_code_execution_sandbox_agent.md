# Agent 32 — The Code-Execution Sandbox Agent

### Agent 32 — The Code-Execution Sandbox Agent

*Executes model-generated code in an isolated environment with recoverable failure semantics.*

#### The Problem

Generated code is a liability and an asset at the same time. It lets the agent do things that no fixed toolset can (like analyze a one-off CSV, transform an unusual data shape, or fit an ad-hoc model), but only if the execution environment is sandboxed against the consequences of getting it wrong. Without sandboxing, model-generated code is, structurally, remote code execution from a probabilistic source. That's approximately the worst possible posture.

The general problem is **safe, reproducible code execution from untrusted-by-construction sources**: providing a substrate on which the agent can run arbitrary code without the consequences leaking past the sandbox boundary.

#### Why Naïve Approaches Fail

- 

*"Just* `eval` *it."* Code injection from prompts, escape from your process, data leaks via filesystem or network.

- 

*"Run it in a subprocess with the same user."* Better than eval, no real isolation. Still has access to the filesystem, network, environment.

- 

*"Run it in a Docker container."* Better, but containers share kernel and have a non-trivial attack surface. Without resource limits a runaway script can DoS the host.

#### The Mechanism

Per-call ephemeral sandboxes with explicit resource caps. Network egress restricted to an allowlist required for the task. Persistent state shared with the sandbox only via a typed mount. Structured output capture distinct from stdout. A failure classifier that maps sandbox exits to actionable feedback.

![Pattern 056 — Agent 32 — The Code-Execution Sandbox Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df5531a4154e443218e_codex-pattern-056-agent-32-the-code-execution-sandbox-agent-the-mechanism.png)

```python
# tools/sandbox.py
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
```

#### Trade-offs and Alternatives

The sandbox approach has real latency cost per call (Docker startup is hundreds of milliseconds at minimum) and operational complexity (the container runtime is itself a system that has to be maintained, secured, and scaled).

For agents that execute code rarely, the overhead is acceptable. For agents that execute code on every step, the latency budget for the sandbox itself becomes a constraint.

Lower-overhead alternatives include Python `RestrictedPython`, Web Workers for JavaScript, V8 isolates, and WebAssembly sandboxes. Each has its own trade-off in completeness, performance, and security. Pick based on the threat model: untrusted user data passing through the sandbox is a higher bar than untrusted model-generated code that the agent fully controls.

#### Production Failure Modes

- 

**Sandbox escape:** Despite the best efforts, container/VM escape vulnerabilities exist. Mitigate by running the sandbox host with minimal capabilities, blast-radius isolation (one customer's sandbox cannot reach another's data), and continuous security patching.

- 

**Resource-limit evasion:** Code that fork-bombs, allocates slowly to evade memory limits, or pegs CPU just under the limit. Mitigate by enforcing wall-time as the master limit. Nothing escapes a wall-time kill.

- 

**Side-channel leakage:** Code that reads timing or other side channels to infer information from the host. Mitigate by minimizing what the host has that's worth leaking. The sandbox host should hold no secrets the sandboxed code shouldn't see.

#### Case Study

A data-analysis agent at a business-intelligence vendor exposes a sandboxed Python environment with a curated set of libraries (pandas, numpy, scikit-learn, matplotlib), allowing analysts to ask any question over their data without the agent ever needing a hardcoded analytical tool. Median sandbox-execution latency is 1.8 seconds. The sandbox-escape rate measured against red-team exercises is zero across two years of operation.

The pattern is responsible for the agent handling approximately 70% of ad-hoc analytics requests at customer sites end-to-end.

**Pairs with:** Side-Effect Auditor (Agent 37), Refusal Calibrator (Agent 54), Browser-Driver (Agent 34).
