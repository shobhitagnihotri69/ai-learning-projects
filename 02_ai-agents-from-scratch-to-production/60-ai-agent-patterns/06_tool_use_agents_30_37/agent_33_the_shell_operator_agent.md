# Agent 33 — The Shell-Operator Agent

### Agent 33 — The Shell-Operator Agent

*Drives a Unix shell with explicit safety policies and rollback semantics.*

#### The Problem

When the agent's environment is a real system rather than an API, the natural tool is a shell. A shell is also the single most dangerous tool the agent can have: a misplaced `rm`, a sloppy redirect, or a wrong-directory `chmod` can destroy state that no rollback can recover. The default "give the agent shell access" posture is the worst-case combination of power and risk.

The general problem is **shell access with structural safety**: making shell-driven actions possible without making catastrophic mistakes possible.

#### Why Naïve Approaches Fail

- 

*"Just exec what the model says."* Production incident, eventually.

- 

*"Allowlist commands."* Works until you need to compose them. The model will find combinations the allowlist didn't anticipate.

- 

*"Run the shell as a low-privilege user."* Necessary but not sufficient. Even an unprivileged shell can destroy the user's own files.

#### The Mechanism

A command interpreter that parses and classifies commands before execution. A denylist combined with an allowlist for state-modifying operations. A snapshot policy for the working tree before any state-modifying batch. A confirmation gate that surfaces dangerous operations to the operator at policy-defined risk thresholds.

![Pattern 057 — Agent 33 — The Shell-Operator Agent — The Mechanism](https://cdn.prod.website-files.com/670b041cc58f983b09ee069a/6a7f5df5c3c147f0711e6993_codex-pattern-057-agent-33-the-shell-operator-agent-the-mechanism.png)

```python
# tools/shell_operator.py
from dataclasses import dataclass, field
import subprocess, shlex, hashlib, tarfile, tempfile, os
from pathlib import Path
from enum import Enum

class CommandClass(Enum):
    READ_ONLY = "read_only"
    STATE_MODIFYING = "state_modifying"
    DESTRUCTIVE = "destructive"
    FORBIDDEN = "forbidden"

DESTRUCTIVE_COMMANDS = {"rm", "shred", "mkfs", "dd", "fdisk", "shutdown", "reboot"}
STATE_MODIFYING_COMMANDS = {"git", "npm", "pip", "make", "cp", "mv", "mkdir", "chmod", "chown"}
READ_ONLY_COMMANDS = {"ls", "cat", "grep", "find", "head", "tail", "wc", "pwd", "echo"}

@dataclass
class ShellResult:
    command: str
    classification: CommandClass
    executed: bool
    stdout: str
    stderr: str
    exit_code: int
    snapshot_id: str | None = None

class ShellOperatorAgent:
    def __init__(self, working_dir: Path, *, confirmation_callback=None,
                 allow_destructive: bool = False):
        self.working_dir = working_dir
        self.confirm = confirmation_callback or (lambda cmd: False)
        self.allow_destructive = allow_destructive
        self._snapshots = {}
    
    def execute(self, command: str) -> ShellResult:
        cls = self._classify(command)
        if cls == CommandClass.FORBIDDEN:
            return ShellResult(command=command, classification=cls, executed=False,
                               stdout="", stderr="forbidden", exit_code=1)
        if cls == CommandClass.DESTRUCTIVE:
            if not self.allow_destructive:
                return ShellResult(command=command, classification=cls, executed=False,
                                   stdout="", stderr="destructive_not_permitted", exit_code=1)
            if not self.confirm(command):
                return ShellResult(command=command, classification=cls, executed=False,
                                   stdout="", stderr="operator_denied", exit_code=1)
        snapshot_id = None
        if cls in (CommandClass.STATE_MODIFYING, CommandClass.DESTRUCTIVE):
            snapshot_id = self._snapshot()
        proc = subprocess.run(
            command, shell=True, cwd=self.working_dir,
            capture_output=True, text=True, timeout=60,
        )
        return ShellResult(
            command=command, classification=cls, executed=True,
            stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode,
            snapshot_id=snapshot_id,
        )
    
    def rollback(self, snapshot_id: str) -> bool:
        if snapshot_id not in self._snapshots:
            return False
        archive = self._snapshots[snapshot_id]
        # Wipe working dir contents, restore from archive
        for item in self.working_dir.iterdir():
            if item.is_dir():
                subprocess.run(["rm", "-rf", str(item)], check=True)
            else:
                item.unlink()
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(self.working_dir)
        return True
    
    def _classify(self, command: str) -> CommandClass:
        # Parse pipes, redirects, command substitutions
        tokens = shlex.split(command)
        if not tokens:
            return CommandClass.FORBIDDEN
        head = tokens[0]
        # Forbidden patterns (sudo, escape characters, etc.)
        if head in ("sudo", "su") or "&&" in command or "||" in command:
            # Multi-command shells require per-segment analysis
            return self._classify_compound(command)
        if head in DESTRUCTIVE_COMMANDS:
            return CommandClass.DESTRUCTIVE
        if head in STATE_MODIFYING_COMMANDS:
            return CommandClass.STATE_MODIFYING
        if head in READ_ONLY_COMMANDS:
            return CommandClass.READ_ONLY
        return CommandClass.FORBIDDEN
    
    def _snapshot(self) -> str:
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            with tarfile.open(tmp.name, "w:gz") as tf:
                tf.add(self.working_dir, arcname=".")
            snap_id = hashlib.sha256(open(tmp.name, "rb").read()).hexdigest()[:16]
            self._snapshots[snap_id] = tmp.name
        return snap_id
```

#### Trade-offs and Alternatives

Shell access is the highest-power, highest-risk tool category. Snapshotting before every modifying batch costs disk and latency.

For agents that operate in append-only or version-controlled environments (like a Git working tree or an object store with versioning), the snapshot can be replaced by a cheaper bookmark (the current commit or the current version stamp). The classifier needs continuous tuning against the agent's actual command patterns.

For environments where you can avoid shell access entirely like a typed API to the same underlying system, do that. The shell is a last resort.

#### Production Failure Modes

- 

**Classifier evasion:** The model issues a command that evades classification through obfuscation (using `find ... -delete` instead of `rm`, command substitution that hides the destructive head). Mitigate by classifying the *effects* via a tracing wrapper rather than only by parsing the literal command.

- 

**Rollback drift:** Snapshots accumulate, storage fills up. Apply a retention policy (the Forgetting-Policy Agent, Agent 26, applies here).

- 

**Working-dir escape:** A command writes outside the working directory (absolute paths, symlinks). Mitigate by sandboxing the shell itself in a chroot or container.

#### Case Study

A developer-environment agent at a developer-tools company bootstraps new repositories on a developer's machine (clone, install dependencies, run setup scripts) under a shell-operator that snapshots the working state at the start and rolls back on any non-zero exit. The rollback path is invoked roughly 4% of the time. In the absence of the snapshot mechanism, those failures historically required manual cleanup.

The pattern's deployment was credited with eliminating "agent left my machine in a weird state" as a customer complaint category.

**Pairs with:** Code-Execution Sandbox (Agent 32), Side-Effect Auditor (Agent 37), Constitution-Bound (Agent 53).
