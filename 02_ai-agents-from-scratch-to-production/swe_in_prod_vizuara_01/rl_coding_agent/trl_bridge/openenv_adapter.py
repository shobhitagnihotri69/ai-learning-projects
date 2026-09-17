"""Hugging Face TRL and OpenEnv compatibility bridge for RL coding agents.

Exposes standard gym/OpenEnv-style step and reward protocols for integration with
trl.GRPOTrainer and open-source RL frameworks.
"""

from typing import Any, Dict, List, Optional, Tuple
from environments.base import BaseCodingEnv
from environments import get_environment
from rewards.composite import CompositeReward


class OpenEnvCodingAdapter:
    """Adapter conforming to OpenEnv / gym environment conventions."""

    def __init__(
        self,
        task_instance: Optional[Dict[str, Any]] = None,
        use_docker: bool = False,
        reward_fn: Optional[CompositeReward] = None
    ):
        self.task_instance = task_instance or {}
        self.use_docker = use_docker
        self.env: Optional[BaseCodingEnv] = None
        self.reward_fn = reward_fn or CompositeReward()
        self.current_step = 0
        self.max_steps = 10

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """Reset environment to task initial state."""
        if self.env is not None:
            self.env.close()

        self.env = get_environment(use_docker=self.use_docker)
        initial_files = (options or {}).get("initial_files") or self.task_instance.get("files")
        obs = self.env.reset(initial_files=initial_files)
        self.current_step = 0

        info = {
            "task_id": self.task_instance.get("instance_id", "custom_task"),
            "status": "ready"
        }
        return obs, info

    def step(self, action: str) -> Tuple[str, float, bool, bool, Dict[str, Any]]:
        """Execute action (bash command), calculate step reward, and check termination.
        
        Returns:
            observation (str), reward (float), terminated (bool), truncated (bool), info (dict)
        """
        if self.env is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        self.current_step += 1
        obs = self.env.run(action)
        patch = self.env.patch()

        truncated = self.current_step >= self.max_steps
        terminated = False

        # If agent runs a test or reaches max steps, evaluate composite reward
        is_test_step = "pytest" in action or "python -m unittest" in action
        if is_test_step or truncated:
            reward_data = self.reward_fn.evaluate(
                env=self.env,
                patch=patch,
                expected_passing_tests=self.task_instance.get("FAIL_TO_PASS")
            )
            reward = reward_data["total_reward"]
            if reward_data.get("passed"):
                terminated = True
        else:
            reward = 0.0
            reward_data = {"note": "intermediate step"}

        info = {
            "patch": patch,
            "calls_count": len(self.env.calls),
            "step": self.current_step,
            "reward_details": reward_data
        }

        return obs, reward, terminated, truncated, info

    def close(self):
        """Tear down active sandbox."""
        if self.env is not None:
            self.env.close()
            self.env = None


def make_trl_env(task_instance: Dict[str, Any], use_docker: bool = False):
    """Factory function directly compatible with TRL GRPOTrainer environment_factory."""
    def _thunk():
        return OpenEnvCodingAdapter(task_instance=task_instance, use_docker=use_docker)
    return _thunk
