"""Local subprocess sandbox environment with git-tracked state.

Zero Docker dependencies. Works out-of-the-box on Hugging Face Spaces free tier,
Google Colab, Kaggle, macOS, and Linux.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, Optional

from environments.base import BaseCodingEnv


class LocalSandboxEnv(BaseCodingEnv):
    """An isolated local filesystem sandbox backed by git tracking and bash execution."""

    def __init__(self, timeout: int = 30, max_output_chars: int = 4000):
        self.timeout = timeout
        self.max_output_chars = max_output_chars
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self.workdir: Optional[str] = None
        self.bin_dir: Optional[str] = None
        self.env_vars: Dict[str, str] = {}
        self.calls = []

    def reset(self, initial_files: Optional[Dict[str, str]] = None) -> str:
        """Create a fresh workspace, initialize git tracking, and write seed files."""
        self.close()
        self._temp_dir = tempfile.TemporaryDirectory(prefix="rl_env_")
        self.workdir = self._temp_dir.name
        self.calls = []

        # Setup custom bin dir to ensure 'python' aliases to current python executable
        self.bin_dir = os.path.join(self.workdir, ".sandbox_bin")
        os.makedirs(self.bin_dir, exist_ok=True)
        py_symlink = os.path.join(self.bin_dir, "python")
        if not os.path.exists(py_symlink):
            try:
                os.symlink(sys.executable, py_symlink)
            except Exception:
                pass

        self.env_vars = os.environ.copy()
        self.env_vars["PATH"] = f"{self.bin_dir}:{self.env_vars.get('PATH', '')}"

        # Initialize git repository
        self._exec_cmd(["git", "init", "-q"])
        self._exec_cmd(["git", "config", "user.name", "RL Agent"])
        self._exec_cmd(["git", "config", "user.email", "agent@rl.local"])

        if initial_files:
            for rel_path, content in initial_files.items():
                full_path = os.path.join(self.workdir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

            self._exec_cmd(["git", "add", "-A"])
            self._exec_cmd(["git", "commit", "-m", "Initial commit", "--quiet"])

        return f"Environment initialized at {self.workdir}"

    def run(self, cmd: str) -> str:
        """Execute a bash command in the isolated workspace with timeout guard."""
        if not self.workdir:
            self.reset()

        self.calls.append(cmd)
        try:
            res = subprocess.run(
                ["bash", "-c", cmd],
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=self.env_vars
            )
            output = res.stdout
            if res.stderr:
                output += ("\n" if output else "") + res.stderr
            if not output.strip():
                output = f"(Process exited with return code {res.returncode}, no output)"
        except subprocess.TimeoutExpired:
            output = f"Command timed out after {self.timeout} seconds."
        except Exception as e:
            output = f"Execution error: {str(e)}"

        if len(output) > self.max_output_chars:
            output = output[:self.max_output_chars] + f"\n... [Truncated. Total output: {len(output)} chars]"

        return output

    def patch(self) -> str:
        """Return the git diff of all modifications made since reset."""
        if not self.workdir:
            return ""
        # Diff tracked files and untracked files
        res = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=self.workdir,
            capture_output=True,
            text=True
        )
        diff = res.stdout.strip()
        if not diff:
            # Check for newly added untracked files
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.workdir,
                capture_output=True,
                text=True
            ).stdout.strip()
            if status:
                subprocess.run(["git", "add", "-N", "."], cwd=self.workdir, capture_output=True)
                diff = subprocess.run(
                    ["git", "diff"],
                    cwd=self.workdir,
                    capture_output=True,
                    text=True
                ).stdout.strip()
        return diff

    def _exec_cmd(self, cmd_args):
        return subprocess.run(cmd_args, cwd=self.workdir, capture_output=True, text=True)

    def close(self) -> None:
        """Clean up the temporary workspace directory."""
        if self._temp_dir is not None:
            try:
                self._temp_dir.cleanup()
            except Exception:
                pass
            self._temp_dir = None
            self.workdir = None
