"""Ephemeral Docker container sandbox environment.

Provides full containerized kernel isolation, no-network jail, and memory caps.
Requires Docker daemon to be running.
"""

import os
import shutil
import subprocess
import uuid
from typing import Dict, Optional

from environments.base import BaseCodingEnv


class DockerSandboxEnv(BaseCodingEnv):
    """An ephemeral Docker container execution sandbox for production agent training."""

    def __init__(
        self,
        image: str = "python:3.10-slim",
        mem_limit: str = "1g",
        cpus: float = 1.0,
        network_disabled: bool = True,
        timeout: int = 30,
        max_output_chars: int = 4000
    ):
        self.image = image
        self.mem_limit = mem_limit
        self.cpus = cpus
        self.network_disabled = network_disabled
        self.timeout = timeout
        self.max_output_chars = max_output_chars
        self.container_id: Optional[str] = None
        self.calls = []

    @staticmethod
    def is_available() -> bool:
        """Check if Docker CLI and daemon are available."""
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def reset(self, initial_files: Optional[Dict[str, str]] = None) -> str:
        """Start a new container and populate initial files with git tracking."""
        self.close()
        if not self.is_available():
            raise RuntimeError(
                "Docker daemon is not available. Please start Docker or use LocalSandboxEnv."
            )

        container_name = f"rl_agent_{uuid.uuid4().hex[:8]}"
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-m", self.mem_limit,
            f"--cpus={self.cpus}",
        ]
        if self.network_disabled:
            cmd.extend(["--network", "none"])

        cmd.extend([self.image, "tail", "-f", "/dev/null"])

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to start docker container: {res.stderr}")

        self.container_id = container_name
        self.calls = []

        # Setup working workspace in container
        self.run("mkdir -p /workspace && cd /workspace && git init -q")
        self.run("git config --global user.name 'RL Agent' && git config --global user.email 'agent@rl.local'")

        if initial_files:
            for rel_path, content in initial_files.items():
                # Write file safely using heredoc or sh
                dir_name = os.path.dirname(f"/workspace/{rel_path}")
                self.run(f"mkdir -p {dir_name}")
                # Escape single quotes in content
                escaped_content = content.replace("'", "'\"'\"'")
                self.run(f"printf '%s' '{escaped_content}' > /workspace/{rel_path}")

            self.run("cd /workspace && git add -A && git commit -m 'Initial commit' --quiet")

        return f"Docker sandbox container {self.container_id} started."

    def run(self, cmd: str) -> str:
        """Execute command inside the container with timeout."""
        if not self.container_id:
            self.reset()

        self.calls.append(cmd)
        exec_cmd = [
            "docker", "exec",
            "-w", "/workspace",
            self.container_id,
            "bash", "-c", cmd
        ]

        try:
            res = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            output = res.stdout
            if res.stderr:
                output += ("\n" if output else "") + res.stderr
            if not output.strip():
                output = f"(Process exited with return code {res.returncode}, no output)"
        except subprocess.TimeoutExpired:
            output = f"Command timed out after {self.timeout} seconds."
        except Exception as e:
            output = f"Container execution error: {str(e)}"

        if len(output) > self.max_output_chars:
            output = output[:self.max_output_chars] + f"\n... [Truncated. Total output: {len(output)} chars]"

        return output

    def patch(self) -> str:
        """Extract git diff from the container."""
        if not self.container_id:
            return ""
        diff_res = subprocess.run(
            ["docker", "exec", "-w", "/workspace", self.container_id, "git", "diff", "HEAD"],
            capture_output=True,
            text=True
        )
        diff = diff_res.stdout.strip()
        if not diff:
            # Check untracked files
            subprocess.run(
                ["docker", "exec", "-w", "/workspace", self.container_id, "git", "add", "-N", "."],
                capture_output=True
            )
            diff = subprocess.run(
                ["docker", "exec", "-w", "/workspace", self.container_id, "git", "diff"],
                capture_output=True,
                text=True
            ).stdout.strip()
        return diff

    def close(self) -> None:
        """Stop and remove the ephemeral container."""
        if self.container_id:
            subprocess.run(["docker", "rm", "-f", self.container_id], capture_output=True)
            self.container_id = None
