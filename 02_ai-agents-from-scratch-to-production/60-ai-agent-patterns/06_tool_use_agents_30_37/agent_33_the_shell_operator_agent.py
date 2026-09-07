"""
Agent 33 — The Shell-Operator Agent
Implementation from The AI Agent Engineer's Guide
"""



# ======================================================================# tools/shell_operator.py
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

