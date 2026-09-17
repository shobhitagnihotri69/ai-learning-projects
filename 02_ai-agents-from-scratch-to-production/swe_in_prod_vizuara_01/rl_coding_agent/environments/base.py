"""Base interface for RL Coding Environments."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class BaseCodingEnv(ABC):
    """Abstract base class for coding agent execution environments.
    
    Compatible with Hugging Face OpenEnv and gym-style agent interactions.
    """

    @abstractmethod
    def reset(self, initial_files: Optional[Dict[str, str]] = None) -> str:
        """Reset the environment state and return the initial observation.
        
        Args:
            initial_files: Optional mapping of relative file paths to content.
            
        Returns:
            Initial observation string.
        """
        pass

    @abstractmethod
    def run(self, cmd: str) -> str:
        """Execute a shell command inside the environment sandbox.
        
        Args:
            cmd: Bash command line to execute.
            
        Returns:
            Terminal stdout + stderr string observation.
        """
        pass

    @abstractmethod
    def patch(self) -> str:
        """Generate a unified git diff representing all changes made by the agent.
        
        Returns:
            Unified diff string.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up all sandbox resources, containers, or temporary workspaces."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
