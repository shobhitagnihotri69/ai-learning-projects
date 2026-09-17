"""Environments module for RL Coding Agent."""

from environments.base import BaseCodingEnv
from environments.local_sandbox import LocalSandboxEnv
from environments.docker_sandbox import DockerSandboxEnv


def get_environment(use_docker: bool = False, **kwargs) -> BaseCodingEnv:
    """Factory to instantiate the appropriate execution sandbox.
    
    Args:
        use_docker: If True and Docker is available, returns DockerSandboxEnv.
                   Otherwise returns LocalSandboxEnv.
        **kwargs: Additional options forwarded to sandbox constructor.
        
    Returns:
        Instance conforming to BaseCodingEnv.
    """
    if use_docker:
        if DockerSandboxEnv.is_available():
            return DockerSandboxEnv(**kwargs)
        print("[Warning] Docker daemon unavailable. Falling back to LocalSandboxEnv.")
    return LocalSandboxEnv(**kwargs)


__all__ = ["BaseCodingEnv", "LocalSandboxEnv", "DockerSandboxEnv", "get_environment"]
